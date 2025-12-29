package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
)

type Request struct {
	Username string `json:"username"`
}

type APIResponse struct {
	Status  string      `json:"status"`
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

type UserDetailResponse struct {
	Username  string    `json:"username"`
	UUID      string    `json:"uuid"`
	Quota     QuotaInfo `json:"quota"`
	LoginInfo LoginInfo `json:"login_info"`
}

type QuotaInfo struct {
	LimitBytes   int64  `json:"limit_bytes"`
	LimitDisplay string `json:"limit_display"`
	UsageBytes   int64  `json:"usage_bytes"`
	UsageDisplay string `json:"usage_display"`
}

type LoginInfo struct {
	TotalIPLogin int      `json:"total_ip_login"`
	LastLogin    string   `json:"last_login"`
	ActiveIPs    []string `json:"active_ips"`
}

type NoobzSystemOutput map[string]NoobzDetail

type NoobzDetail struct {
	Password  string    `json:"password"`
	Blocked   bool      `json:"blocked"`
	Expired   int       `json:"expired"`
	Bandwidth int       `json:"bandwidth"`
	Issued    string    `json:"issued"`
	Statistic Statistic `json:"statistic"`
}

type Statistic struct {
	BytesUsage    BytesUsage `json:"bytes_usage"`
	ActiveDevices []string   `json:"active_devices"`
}

type BytesUsage struct {
	Up   int64 `json:"up"`
	Down int64 `json:"down"`
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
		sendErrorResponse(400, "Username is required")
		return
	}

	cmd := exec.Command("noobzvpns", "-j", "print", req.Username)
	output, err := cmd.Output()
	if err != nil {
		sendErrorResponse(404, fmt.Sprintf("User '%s' not found or system error", req.Username))
		return
	}

	var systemData NoobzSystemOutput
	if err := json.Unmarshal(output, &systemData); err != nil {
		sendErrorResponse(500, "Failed to parse system output")
		return
	}

	details, exists := systemData[req.Username]
	if !exists {
		sendErrorResponse(404, fmt.Sprintf("User '%s' data is missing", req.Username))
		return
	}

	limitBytes := int64(details.Bandwidth) * 1024 * 1024 * 1024

	totalUsageBytes := details.Statistic.BytesUsage.Up + details.Statistic.BytesUsage.Down

	limitDisplay := formatBytes(limitBytes)
	usageDisplay := formatBytes(totalUsageBytes)

	activeIPs := details.Statistic.ActiveDevices
	if activeIPs == nil {
		activeIPs = []string{}
	}

	lastLoginStr := "-"
	if len(activeIPs) > 0 {
		lastLoginStr = "Online Now"
	}

	responseData := UserDetailResponse{
		Username: req.Username,
		UUID:     "-",
		Quota: QuotaInfo{
			LimitBytes:   limitBytes,
			LimitDisplay: limitDisplay,
			UsageBytes:   totalUsageBytes,
			UsageDisplay: usageDisplay,
		},
		LoginInfo: LoginInfo{
			TotalIPLogin: len(activeIPs),
			LastLogin:    lastLoginStr,
			ActiveIPs:    activeIPs,
		},
	}

	sendSuccessResponse(responseData)
}

func formatBytes(bytes int64) string {
	if bytes == 0 {
		return "0 B"
	}
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.2f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

func sendSuccessResponse(data UserDetailResponse) {
	resp := APIResponse{
		Status:  "true",
		Code:    200,
		Message: fmt.Sprintf("Detail untuk user '%s' berhasil diambil", data.Username),
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
