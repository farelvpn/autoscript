package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"strings"
)

const (
	PATH_BOT_KEY   = "/etc/xray/bot.key"
	PATH_CLIENT_ID = "/etc/xray/client.id"
	CMD_NOOBZ      = "noobzvpns"
)

type Request struct {
	Username string `json:"username"`
	AddQuota int    `json:"add_quota"`
}

type APIResponse struct {
	Status  string      `json:"status"`
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

type AddQuotaData struct {
	Username           string    `json:"username"`
	QuotaAdded         QuotaInfo `json:"quota_added"`
	PreviousTotalQuota QuotaInfo `json:"previous_total_quota"`
	NewTotalQuota      QuotaInfo `json:"new_total_quota"`
	TelegramNotif      string    `json:"telegram_notification"`
}

type QuotaInfo struct {
	GB        int    `json:"gb"`
	GBDisplay string `json:"gb_display"`
	Bytes     int64  `json:"bytes"`
}

type NoobzAccountDetail struct {
	Password  string `json:"password"`
	Blocked   bool   `json:"blocked"`
	Expired   int    `json:"expired"`
	Bandwidth int    `json:"bandwidth"`
	Devices   int    `json:"devices"`
}

type Config struct {
	TelegramBotToken string
	TelegramChatID   string
}

func main() {
	reader := bufio.NewReader(os.Stdin)
	input, err := io.ReadAll(reader)
	if err != nil {
		sendErrorResponse(500, "Failed to read input")
		return
	}

	var req Request
	if err := json.Unmarshal(input, &req); err != nil {
		sendErrorResponse(400, "Invalid JSON format")
		return
	}

	if req.Username == "" {
		sendErrorResponse(400, "Username required")
		return
	}
	if req.AddQuota <= 0 {
		sendErrorResponse(400, "Add quota must be greater than 0")
		return
	}

	currentUser, err := getUserInfo(req.Username)
	if err != nil {
		sendErrorResponse(404, fmt.Sprintf("User '%s' not found: %v", req.Username, err))
		return
	}

	newTotalGB := currentUser.Bandwidth + req.AddQuota

	cmd := exec.Command(CMD_NOOBZ, "edit", req.Username, "-p", currentUser.Password, "-b", strconv.Itoa(newTotalGB))
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		sendErrorResponse(500, fmt.Sprintf("Failed to update quota system: %v", err))
		return
	}

	data := &AddQuotaData{
		Username: req.Username,
		QuotaAdded: QuotaInfo{
			GB:        req.AddQuota,
			GBDisplay: fmt.Sprintf("%d GB", req.AddQuota),
			Bytes:     gbToBytes(req.AddQuota),
		},
		PreviousTotalQuota: QuotaInfo{
			GB:        currentUser.Bandwidth,
			GBDisplay: fmt.Sprintf("%d GB", currentUser.Bandwidth),
			Bytes:     gbToBytes(currentUser.Bandwidth),
		},
		NewTotalQuota: QuotaInfo{
			GB:        newTotalGB,
			GBDisplay: fmt.Sprintf("%d GB", newTotalGB),
			Bytes:     gbToBytes(newTotalGB),
		},
		TelegramNotif: "not_configured",
	}

	if err := sendTelegramNotification(req.Username, req.AddQuota, newTotalGB); err == nil {
		data.TelegramNotif = "sent"
	} else {
		data.TelegramNotif = "failed"
	}

	sendSuccessResponse(req.Username, data)
}

func getUserInfo(username string) (*NoobzAccountDetail, error) {
	cmd := exec.Command(CMD_NOOBZ, "-j", "print", username)
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	var result map[string]NoobzAccountDetail
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("parse json error: %v", err)
	}

	details, exists := result[username]
	if !exists {
		return nil, fmt.Errorf("user not in output list")
	}

	return &details, nil
}

func gbToBytes(gb int) int64 {
	return int64(gb) * 1024 * 1024 * 1024
}

func sendSuccessResponse(username string, data *AddQuotaData) {
	resp := APIResponse{
		Status:  "true",
		Code:    200,
		Message: fmt.Sprintf("Kuota untuk user '%s' berhasil ditambahkan", username),
		Data:    data,
	}
	jsonResp, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(jsonResp))
}

func sendErrorResponse(code int, message string) {
	resp := APIResponse{
		Status:  "false",
		Code:    code,
		Message: message,
		Data:    nil,
	}
	jsonResp, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(jsonResp))
	os.Exit(1)
}

func sendTelegramNotification(username string, added int, newTotal int) error {
	config, err := readConfig()
	if err != nil || config.TelegramBotToken == "" {
		return fmt.Errorf("config missing")
	}

	msg := fmt.Sprintf(`═══════════════════════════
<b>NoobzVPN Quota Added</b>
<b>════════════════════════════</b>
<b>Username  :</b> <code>%s</code>
<b>Added     :</b> <code>%d GB</code>
<b>New Total :</b> <code>%d GB</code>
<b>════════════════════════════</b>`, username, added, newTotal)

	payload := map[string]string{
		"chat_id":    config.TelegramChatID,
		"text":       msg,
		"parse_mode": "HTML",
	}
	jsonPayload, _ := json.Marshal(payload)

	cmd := exec.Command("curl", "-s", "-X", "POST",
		fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", config.TelegramBotToken),
		"-H", "Content-Type: application/json",
		"-d", string(jsonPayload))

	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func readConfig() (*Config, error) {
	config := &Config{}

	token, err := os.ReadFile(PATH_BOT_KEY)
	if err == nil {
		config.TelegramBotToken = strings.TrimSpace(string(token))
	}

	chatId, err := os.ReadFile(PATH_CLIENT_ID)
	if err == nil {
		config.TelegramChatID = strings.TrimSpace(string(chatId))
	}

	return config, nil
}
