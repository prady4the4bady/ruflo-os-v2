package main

import (
	"encoding/json"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/gorilla/mux"
	"github.com/sirupsen/logrus"
)

// CompletionRequest matches the OpenAI chat/completions API
type CompletionRequest struct {
	Model    string        `json:"model"`
	Messages []ChatMessage `json:"messages"`
	Stream   bool          `json:"stream"`
}

type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type CompletionResponse struct {
	Choices []Choice `json:"choices"`
}

type Choice struct {
	Message ChatMessage `json:"message"`
}

var log = logrus.New()
var registry *ModelRegistry

func handleChatCompletions(w http.ResponseWriter, r *http.Request) {
	var req CompletionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Infof("Received completion request for model: %s", req.Model)

	// Mock response from llama.cpp / router logic
	resp := CompletionResponse{
		Choices: []Choice{
			{
				Message: ChatMessage{
					Role:    "assistant",
					Content: "This is Vyrex responding from the kernel-accelerated local model.",
				},
			},
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func main() {
	log.SetFormatter(&logrus.TextFormatter{FullTimestamp: true})
	log.Info("Starting Vyrex Daemon...")

	registry = NewModelRegistry("/var/vyrex/models/")
	registry.LoadModels()

	router := mux.NewRouter()
	router.HandleFunc("/v1/chat/completions", handleChatCompletions).Methods("POST")
	router.HandleFunc("/v1/models", handleListModels).Methods("GET")
	router.HandleFunc("/v1/models/hotswap", handleHotswapModel).Methods("POST")

	socketPath := "/run/vyrex/api.sock"
	_ = os.Remove(socketPath)
	
	// Create the directory if it doesn't exist
	_ = os.MkdirAll("/run/vyrex", 0755)

	listener, err := net.Listen("unix", socketPath)
	if err != nil {
		log.Fatalf("Failed to listen on unix socket: %v", err)
	}
	defer listener.Close()

	if err := os.Chmod(socketPath, 0666); err != nil {
		log.Fatalf("Failed to chmod unix socket: %v", err)
	}

	go func() {
		log.Infof("Listening on UNIX socket: %s", socketPath)
		if err := http.Serve(listener, router); err != nil {
			log.Fatalf("Server error: %v", err)
		}
	}()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Info("Shutting down Vyrex Daemon...")
}
