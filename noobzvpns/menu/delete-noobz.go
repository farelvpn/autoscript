package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io/ioutil"
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

type DeleteData struct {
	Username     string   `json:"username"`
	UUID         string   `json:"uuid,omitempty"`
	FilesRemoved []string `json:"files_removed"`
}

func main() {
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

	if req.Username == "" {
		sendErrorResponse(400, "Field 'username' is required")
		return
	}

	if err := executeRemoveCommand(req.Username); err != nil {
		sendErrorResponse(500, "Failed to remove account: "+err.Error())
		return
	}

	data := &DeleteData{
		Username: req.Username,
		UUID:     "-",
		FilesRemoved: []string{
			"database_record",
			"config_cache",
		},
	}

	// Kirim response sukses
	sendSuccessResponse(req.Username, data)
}

func executeRemoveCommand(username string) error {
	cmd := exec.Command("noobzvpns", "remove", username)

	cmd.Stderr = os.Stderr

	return cmd.Run()
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

func sendSuccessResponse(username string, data *DeleteData) {
	response := APIResponse{
		Status:  "true",
		Code:    200,
		Message: fmt.Sprintf("Akun '%s' berhasil dihapus permanen", username),
		Data:    data,
	}
	jsonResponse, _ := json.MarshalIndent(response, "", "  ")
	fmt.Println(string(jsonResponse))
}
