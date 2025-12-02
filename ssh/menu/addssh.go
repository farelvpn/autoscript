package main

import (
	"fmt"
	"os"
)

func clearScrenn() {
	fmt.Print("\033[H\033[2J")
}

func main() {
	clearScrenn()
	fmt.Println("Wait mikir!")
	os.Exit(0)
}
