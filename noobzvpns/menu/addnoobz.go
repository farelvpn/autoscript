package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"os/exec"
	"strings"
	"time"
)

const (
	PATH_BOT_KEY   = "/etc/xray/bot.key"
	PATH_CLIENT_ID = "/etc/xray/client.id"
	PATH_DOMAIN    = "/etc/xray/domain"
)

type Request struct {
	User  string `json:"user"`
	Quota int    `json:"quota"`
}

type APIResponse struct {
	Status  string      `json:"status"`
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

type AccountData struct {
	Username string   `json:"username"`
	Password string   `json:"password"`
	Domain   string   `json:"domain"`
	Limits   Limits   `json:"limits"`
	Ports    Ports    `json:"ports"`
	Paths    []string `json:"paths"`
	Payload  string   `json:"payload"`
}

type Limits struct {
	QuotaGB      int    `json:"quota_gb"`
	QuotaDisplay string `json:"quota_display"`
	QuotaBytes   int64  `json:"quota_bytes"`
}

type Ports struct {
	HTTP  []string `json:"http"`
	HTTPS []string `json:"https"`
}

type Config struct {
	TelegramBotToken string `json:"telegram_bot_token"`
	TelegramChatID   string `json:"telegram_chat_id"`
	Domain           string `json:"domain"`
}

type TelegramMessage struct {
	ChatID    string `json:"chat_id"`
	Text      string `json:"text"`
	ParseMode string `json:"parse_mode"`
}

func main() {
	rand.Seed(time.Now().UnixNano())

	reader := bufio.NewReader(os.Stdin)
	input, err := ioutil.ReadAll(reader)
	if err != nil {
		sendErrorResponse(500, "Failed to read input: "+err.Error())
		return
	}

	var req Request
	if err := json.Unmarshal(input, &req); err != nil {
		sendErrorResponse(400, "Invalid JSON format: "+err.Error())
		return
	}

	if req.User == "" {
		sendErrorResponse(400, "Field 'user' is required")
		return
	}
	if req.Quota <= 0 {
		sendErrorResponse(400, "Field 'quota' must be greater than 0")
		return
	}

	config, err := readConfig()
	if err != nil {
		sendErrorResponse(500, "Failed to read configuration: "+err.Error())
		return
	}

	password := generateRandomPassword(12)

	accountData := createAccountData(config, req.User, password, req.Quota)

	if err := executeNoobzvpnsCommand(req.User, password, req.Quota); err != nil {
		sendErrorResponse(500, "Failed to create account in system: "+err.Error())
		return
	}

	if err := sendTelegramNotification(config, accountData); err != nil {
		fmt.Fprintf(os.Stderr, "Warning: Failed to send Telegram notification: %v\n", err)
	}

	sendSuccessResponse(accountData)
}

func readConfig() (*Config, error) {
	config := &Config{}

	botTokenBytes, err := ioutil.ReadFile(PATH_BOT_KEY)
	if err == nil {
		config.TelegramBotToken = strings.TrimSpace(string(botTokenBytes))
	}

	chatIDBytes, err := ioutil.ReadFile(PATH_CLIENT_ID)
	if err == nil {
		config.TelegramChatID = strings.TrimSpace(string(chatIDBytes))
	}

	domainBytes, err := ioutil.ReadFile(PATH_DOMAIN)
	if err != nil {
		return nil, fmt.Errorf("failed to read %s: %v", PATH_DOMAIN, err)
	}
	config.Domain = strings.TrimSpace(string(domainBytes))

	return config, nil
}

func generateRandomPassword(length int) string {
	chars := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	result := make([]byte, length)
	for i := range result {
		result[i] = chars[rand.Intn(len(chars))]
	}
	return string(result)
}

func createAccountData(config *Config, user, password string, quota int) *AccountData {
	quotaBytes := int64(quota) * 1024 * 1024 * 1024

	return &AccountData{
		Username: fmt.Sprintf("%s@fn-project", user),
		Password: password,
		Domain:   config.Domain,
		Limits: Limits{
			QuotaGB:      quota,
			QuotaDisplay: fmt.Sprintf("%d GB", quota),
			QuotaBytes:   quotaBytes,
		},
		// Konfigurasi Port dan Path yang disederhanakan sesuai permintaan
		Ports: Ports{
			HTTP:  []string{"80", "8880"},
			HTTPS: []string{"443"},
		},
		Paths:   []string{"/noobz"},
		Payload: "GET /noobz HTTP/1.1[crlf]Host: [host][crlf]Upgrade: websocket[crlf][crlf]",
	}
}

func executeNoobzvpnsCommand(user, password string, quota int) error {
	cmd := exec.Command("noobzvpns", "add", user, "-p", password, "-b", fmt.Sprintf("%d", quota))
	cmd.Stderr = os.Stderr // Silent stdout
	return cmd.Run()
}

func sendTelegramNotification(config *Config, account *AccountData) error {
	if config.TelegramBotToken == "" || config.TelegramChatID == "" {
		return nil
	}

	message := formatTelegramMessage(account)

	telegramMsg := TelegramMessage{
		ChatID:    config.TelegramChatID,
		Text:      message,
		ParseMode: "HTML",
	}

	msgJSON, err := json.Marshal(telegramMsg)
	if err != nil {
		return err
	}

	cmd := exec.Command("curl", "-s", "-X", "POST",
		fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", config.TelegramBotToken),
		"-H", "Content-Type: application/json",
		"-d", string(msgJSON))

	return cmd.Run()
}

func formatTelegramMessage(account *AccountData) string {
	httpPorts := strings.Join(account.Ports.HTTP, ", ")
	httpsPorts := strings.Join(account.Ports.HTTPS, ", ")
	paths := strings.Join(account.Paths, ", ")

	return fmt.Sprintf(`═══════════════════════════
<b>NoobzVPN Account Created</b>
<b>════════════════════════════</b>
<b>Hostname  :</b> <code>%s</code>
<b>Username  :</b> <code>%s</code>
<b>Password  :</b> <code>%s</code>
<b>════════════════════════════</b>
<b>Path:</b> <code>%s</code>
<b>════════════════════════════</b>
<b>Limit Badwidth:</b> <code>%s</code>
<b>════════════════════════════</b>
<b>HTTP      :</b> <code>%s</code>
<b>HTTP(S)   :</b> <code>%s</code>
<b>════════════════════════════</b>
<b>PAYLOAD   :</b> <code>%s</code>
<b>════════════════════════════</b>`,
		account.Domain,
		account.Username,
		account.Password,
		paths,
		account.Limits.QuotaDisplay,
		httpPorts,
		httpsPorts,
		account.Payload)
}

func sendErrorResponse(code int, message string) {
	response := APIResponse{
		Status:  "false",
		Code:    code,
		Message: message,
		Data:    nil,
	}
	jsonResponse, _ := json.MarshalIndent(response, "", "  ")
	fmt.Println(string(jsonResponse))
	os.Exit(1)
}

func sendSuccessResponse(data *AccountData) {
	response := APIResponse{
		Status:  "true",
		Code:    201,
		Message: "NoobzVPN account created successfully",
		Data:    data,
	}
	jsonResponse, _ := json.MarshalIndent(response, "", "  ")
	fmt.Println(string(jsonResponse))
}
