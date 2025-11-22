/*
Copyright by Farell Aditya Pratama Putra Utama

Code ini dibuat secara publik & open source jadi jangan sembarang mengubah credit.
Port Default berjalan pada port 9000;

if you wan't run this server api to use another port just use flags -p example:
/path/to/binary/server-api -p 3000 (to run server api use port 3000)

Telegram: @farellvpn | Farell Aditya
*/
package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const (
	TokenPath   = "/etc/api/key"
	ScriptDir   = "/usr/local/sbin/api"
	ExecTimeout = 30 * time.Second
	LogFilePath = "/var/log/api.log"
)

var (
	validTokens = make(map[string]bool)
	tokenMutex  sync.RWMutex
	serverPort  string
)

type APIResponse struct {
	Status  bool        `json:"status"`
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

func loadTokens() {
	file, err := os.Open(TokenPath)
	if err != nil {
		log.Printf("Failed to load tokens: %v", err)
		return
	}
	defer file.Close()

	tokenMutex.Lock()
	validTokens = make(map[string]bool)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if t := strings.TrimSpace(scanner.Text()); t != "" {
			validTokens[t] = true
		}
	}
	tokenMutex.Unlock()
	log.Printf("Tokens loaded. Count: %d", len(validTokens))
}

func respondJSON(w http.ResponseWriter, code int, status bool, message string, data interface{}, errStr string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(APIResponse{
		Status:  status,
		Code:    code,
		Message: message,
		Data:    data,
		Error:   errStr,
	})
}

func respondHTML(w http.ResponseWriter, content string) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(content))
}

func WebHandler(w http.ResponseWriter, r *http.Request) {
	htmlContent := `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Restricted Area</title><style>body{background-color:#000;color:#0f0;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;font-family:'Courier New',Courier,monospace;overflow:hidden}.container{text-align:center;position:relative}h1{font-size:3rem;text-transform:uppercase;letter-spacing:5px;animation:glitch 1s infinite}.eye{font-size:5rem;margin-bottom:20px}@keyframes glitch{0%{transform:translate(0)}20%{transform:translate(-2px,2px)}40%{transform:translate(-2px,-2px)}60%{transform:translate(2px,2px)}80%{transform:translate(2px,-2px)}100%{transform:translate(0)}}</style></head><body><div class="container"><div class="eye">👁️</div><h1>I'M WATCHING YOU</h1><p>Access Restricted. System Logs Recorded.</p><p style="color:#555;font-size:0.8rem;">IP: ` + r.RemoteAddr + `</p></div></body></html>`
	log.Printf("Suspicious web access from %s on %s", r.RemoteAddr, r.URL.Path)
	respondHTML(w, htmlContent)
}

func APIHandler(w http.ResponseWriter, r *http.Request) {
	cleanPath := filepath.Clean(strings.TrimPrefix(r.URL.Path, "/"))
	if strings.Contains(cleanPath, "..") || strings.HasPrefix(cleanPath, "/") {
		respondJSON(w, http.StatusForbidden, false, "Invalid path structure", nil, "Path traversal attempt detected")
		return
	}

	scriptPath := filepath.Join(ScriptDir, cleanPath)
	if info, err := os.Stat(scriptPath); os.IsNotExist(err) || info.IsDir() {
		respondJSON(w, http.StatusNotFound, false, "Script endpoint not found", nil, "File does not exist")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), ExecTimeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, scriptPath)
//	cmd.Env = append(os.Environ(), "REQUEST_METHOD="+r.Method)
	cmd.Env = append(os.Environ(), "REQUEST_METHOD="+r.Method, "TERM=dumb")

	if r.Method == http.MethodPost || r.Method == http.MethodPut {
		if body, err := io.ReadAll(r.Body); err == nil {
			cmd.Stdin = strings.NewReader(string(body))
		}
	}

	output, err := cmd.CombinedOutput()

	if ctx.Err() == context.DeadlineExceeded {
		log.Printf("Timeout executing %s", cleanPath)
		respondJSON(w, http.StatusGatewayTimeout, false, "Execution timed out", nil, "Script took too long")
		return
	}

	if err != nil {
		log.Printf("Execution failed for %s: %v", cleanPath, err)
		var raw json.RawMessage
		if jsonErr := json.Unmarshal(output, &raw); jsonErr == nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			w.Write(output)
		} else {
			respondJSON(w, http.StatusInternalServerError, false, "Internal Script Error", nil, string(output))
		}
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(output)
	log.Printf("Success: %s", cleanPath)
}

func LoggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s | Remote: %s | Time: %v", r.Method, r.URL.Path, r.RemoteAddr, time.Since(start))
	})
}

func AuthMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" || r.URL.Path == "/index.html" {
			WebHandler(w, r)
			return
		}

		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			respondJSON(w, http.StatusUnauthorized, false, "Unauthorized", nil, "Missing Authorization header")
			return
		}

		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			respondJSON(w, http.StatusUnauthorized, false, "Unauthorized", nil, "Invalid token format")
			return
		}

		tokenMutex.RLock()
		isValid := validTokens[parts[1]]
		tokenMutex.RUnlock()

		if !isValid {
			loadTokens()
			tokenMutex.RLock()
			isValid = validTokens[parts[1]]
			tokenMutex.RUnlock()

			if !isValid {
				log.Printf("Unauthorized access attempt: %s", r.RemoteAddr)
				respondJSON(w, http.StatusUnauthorized, false, "Unauthorized", nil, "Invalid token")
				return
			}
		}

		next(w, r)
	}
}

func checkPort(port string) {
	listener, err := net.Listen("tcp", ":"+port)
	if err != nil {
		fmt.Println("Port Already use")
		os.Exit(1)
	}
	listener.Close()
}

func main() {
	portFlag := flag.String("p", "9000", "Port to run the server on")
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage of %s:\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  -p string\n\tPort to run the server on (default \"9000\")\n")
		fmt.Fprintf(os.Stderr, "  --help\n\tShow this help message\n")
	}
	flag.Parse()
	serverPort = *portFlag

	checkPort(serverPort)

	logFile, err := os.OpenFile(LogFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		fmt.Printf("Failed to open log file: %v\n", err)
		os.Exit(1)
	}
	defer logFile.Close()

	multiWriter := io.MultiWriter(os.Stdout, logFile)
	log.SetOutput(multiWriter)
	log.SetFlags(log.Ldate | log.Ltime | log.Lmicroseconds | log.Lshortfile)

	log.Printf("Starting API Server on port %s...", serverPort)

	loadTokens()

	mux := http.NewServeMux()
	mux.HandleFunc("/", AuthMiddleware(APIHandler))

	srv := &http.Server{
		Addr:         ":" + serverPort,
		Handler:      LoggingMiddleware(mux),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 40 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
