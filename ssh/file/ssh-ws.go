/*
 Copyright (c) 2025 Risqi Nur Fadilah

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 DEALINGS IN THE SOFTWARE.

 Thanks To:
 - Rerechan02 [ Reference WebSocket Tunnel ]
 - Dimas Anwar S. A. [ Testing ]
*/

/*

CMD Compile:
CGO_ENABLED=0 go build -ldflags "-s -w -X 'main.Credits=Farell Aditya' -X 'main.Version=v1.0-Stable'" -o ssh-ws

Minimal:
- Debian 11
- Ubuntu 22.04
- go version go1.22.0 linux/amd64

*/

package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

var (
	Version = "1.0.1"
	Credits = "Farell Aditya"
)

const (
	ColorReset  = "\033[0m"
	ColorRed    = "\033[31m"
	ColorGreen  = "\033[32m"
	ColorYellow = "\033[33m"
	ColorCyan   = "\033[36m"
	ColorGray   = "\033[90m"
	ColorPurple = "\033[35m"
)

const (
	DefaultPort     = 8080
	DefaultBind     = "0.0.0.0"
	DefaultTarget   = "127.0.0.1:22"
	DefaultTimeout  = 10 * time.Second
	LogInterval     = 10 * time.Second
	PayloadResponse = "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n"
)

type Config struct {
	BindAddr     string
	Port         int
	Password     string
	FallbackAddr string
	LogFile      string
}

type WriteCounter struct {
	Writer  io.Writer
	Counter *int64
}

func (wc WriteCounter) Write(p []byte) (int, error) {
	n, err := wc.Writer.Write(p)
	if n > 0 {
		atomic.AddInt64(wc.Counter, int64(n))
	}
	return n, err
}

func main() {
	var (
		bindAddr     string
		port         int
		password     string
		fallbackAddr string
		logFile      string
		showHelp     bool
	)

	flag.StringVar(&bindAddr, "b", DefaultBind, "IP Address binding")
	flag.StringVar(&bindAddr, "bind", DefaultBind, "IP Address binding")
	flag.IntVar(&port, "p", DefaultPort, "Port server")
	flag.IntVar(&port, "port", DefaultPort, "Port server")
	flag.StringVar(&password, "a", "", "Password otentikasi")
	flag.StringVar(&password, "auth", "", "Password otentikasi")
	flag.StringVar(&fallbackAddr, "t", DefaultTarget, "Fallback target IP:Port")
	flag.StringVar(&fallbackAddr, "target", DefaultTarget, "Fallback target")
	flag.StringVar(&logFile, "l", "", "File log output")
	flag.StringVar(&logFile, "logs", "", "File log output")
	flag.BoolVar(&showHelp, "h", false, "Bantuan")
	flag.BoolVar(&showHelp, "help", false, "Bantuan")

	flag.Usage = printCustomHelp
	flag.Parse()

	if showHelp {
		printCustomHelp()
		os.Exit(0)
	}

	cfg := Config{
		BindAddr:     bindAddr,
		Port:         port,
		Password:     password,
		FallbackAddr: fallbackAddr,
		LogFile:      logFile,
	}

	setupLogger(cfg.LogFile)
	startServer(cfg)
}

func setupLogger(path string) {
	writers := []io.Writer{os.Stdout}
	if path != "" {
		dir := filepath.Dir(path)
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			_ = os.MkdirAll(dir, 0755)
		}
		file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			log.Printf("%s[!] Gagal log file: %v%s", ColorRed, err, ColorReset)
		} else {
			writers = append(writers, file)
		}
	}
	multi := io.MultiWriter(writers...)
	log.SetOutput(multi)
	log.SetFlags(log.Ldate | log.Ltime)
}

func startServer(cfg Config) {
	addr := fmt.Sprintf("%s:%d", cfg.BindAddr, cfg.Port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		logError("Gagal memulai server", err)
		os.Exit(1)
	}
	defer listener.Close()

	printBanner()
	logInfo(fmt.Sprintf("Server berjalan di: %s%s%s", ColorCyan, addr, ColorReset))
	logInfo(fmt.Sprintf("Default Target: %s%s%s", ColorCyan, cfg.FallbackAddr, ColorReset))
	if cfg.LogFile != "" {
		logInfo(fmt.Sprintf("Logging ke file: %s%s%s", ColorYellow, cfg.LogFile, ColorReset))
	}
	fmt.Println(strings.Repeat("-", 60))

	for {
		conn, err := listener.Accept()
		if err != nil {
			continue
		}
		go handleConnection(conn, cfg)
	}
}

func handleConnection(clientConn net.Conn, cfg Config) {
	defer clientConn.Close()

	clientConn.SetReadDeadline(time.Now().Add(5 * time.Second))
	buf := make([]byte, 4096)
	n, err := clientConn.Read(buf)
	if err != nil {
		return
	}
	clientConn.SetReadDeadline(time.Time{})

	rawHeaders := string(buf[:n])
	targetHost := getHeader(rawHeaders, "X-Real-Host")
	if targetHost == "" {
		targetHost = cfg.FallbackAddr
	}

	authPass := getHeader(rawHeaders, "X-Pass")
	if cfg.Password != "" && authPass != cfg.Password {
		logWarn(fmt.Sprintf("Auth Gagal dari %s", clientConn.RemoteAddr()))
		clientConn.Write([]byte("HTTP/1.1 401 Unauthorized\r\n\r\n"))
		return
	}

	if !strings.Contains(targetHost, ":") {
		targetHost += ":443"
	}

	logSuccess(fmt.Sprintf("Tunnel: %s -> %s%s%s", clientConn.RemoteAddr(), ColorCyan, targetHost, ColorReset))

	targetConn, err := net.DialTimeout("tcp", targetHost, DefaultTimeout)
	if err != nil {
		logError(fmt.Sprintf("Gagal connect ke %s", targetHost), err)
		clientConn.Write([]byte("HTTP/1.1 502 Bad Gateway\r\n\r\n"))
		return
	}
	defer targetConn.Close()

	clientConn.Write([]byte(PayloadResponse))

	doTransferWithMonitoring(clientConn, targetConn, targetHost)
}

func doTransferWithMonitoring(client, target net.Conn, targetName string) {
	var wg sync.WaitGroup

	var tx int64
	var rx int64

	stopMonitor := make(chan bool)

	go func() {
		ticker := time.NewTicker(LogInterval)
		defer ticker.Stop()

		for {
			select {
			case <-stopMonitor:
				return
			case <-ticker.C:
				currentTx := atomic.LoadInt64(&tx)
				currentRx := atomic.LoadInt64(&rx)

				if currentTx > 0 || currentRx > 0 {
					log.Printf("%s[STATUS] %s | TX: %s | RX: %s%s",
						ColorPurple, targetName,
						formatBytes(currentTx),
						formatBytes(currentRx),
						ColorReset)
				}
			}
		}
	}()

	wg.Add(2)

	go func() {
		defer wg.Done()
		writer := WriteCounter{Writer: target, Counter: &tx}
		io.Copy(writer, client)
		target.(*net.TCPConn).CloseWrite()
	}()

	go func() {
		defer wg.Done()
		writer := WriteCounter{Writer: client, Counter: &rx}
		io.Copy(writer, target)
		client.(*net.TCPConn).CloseWrite()
	}()

	wg.Wait()

	stopMonitor <- true
	close(stopMonitor)

	log.Printf("%s[=] Closed: %s | TX: %s | RX: %s%s",
		ColorGray, targetName,
		formatBytes(atomic.LoadInt64(&tx)),
		formatBytes(atomic.LoadInt64(&rx)),
		ColorReset)
}

func formatBytes(b int64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := int64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(b)/float64(div), "KMGTPE"[exp])
}

func printCustomHelp() {
	printBanner()
	fmt.Printf("Usage: %s./ssh-ws [flags]%s\n\n", ColorCyan, ColorReset)
	printFlag("-p, --port", "Port server", fmt.Sprintf("%d", DefaultPort))
	printFlag("-b, --bind", "Bind IP Address", DefaultBind)
	printFlag("-t, --target", "Fallback Target", DefaultTarget)
	printFlag("-l, --logs", "Path File Log", "(none)")
	printFlag("-a, --auth", "Password", "(none)")
}

func printFlag(name, desc, def string) {
	fmt.Printf("  %s%-14s%s %-25s %s(Def: %s)%s\n", ColorYellow, name, ColorReset, desc, ColorGray, def, ColorReset)
}

func printBanner() {
	fmt.Print(ColorCyan)
	fmt.Println(`
   ___  ___  ____  _  ____  __
  / _ \/ _ \/ __ \| |/ /\ \/ /
 / ___/ , _/ /_/ /   |   \  /  
/_/  /_/|_|\____/_/|_|   /_/   `)

	fmt.Printf(" :: GO-TUNNEL PRO :: %s\n", Version)
	fmt.Printf(" :: Developers    :: %s\n", Credits)
	fmt.Println(" :: Telegram      :: @farellvpn")
	fmt.Println()
	fmt.Print(ColorReset)
}

func logInfo(msg string)             { log.Printf("%s[*]%s %s", ColorCyan, ColorReset, msg) }
func logSuccess(msg string)          { log.Printf("%s[+]%s %s", ColorGreen, ColorReset, msg) }
func logWarn(msg string)             { log.Printf("%s[!]%s %s", ColorYellow, ColorReset, msg) }
func logError(msg string, err error) { log.Printf("%s[-]%s %s: %v", ColorRed, ColorReset, msg, err) }
func getHeader(headers, key string) string {
	lines := strings.Split(headers, "\r\n")
	prefix := strings.ToLower(key) + ": "
	for _, line := range lines {
		if strings.HasPrefix(strings.ToLower(line), prefix) {
			return strings.TrimSpace(line[len(prefix):])
		}
	}
	return ""
}
