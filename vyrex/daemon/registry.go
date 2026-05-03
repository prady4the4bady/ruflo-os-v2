package main

import (
	"encoding/json"
	"net/http"
	"sync"
)

// Model represents a registered AI model
type Model struct {
	ID        string `json:"id"`
	Object    string `json:"object"`
	OwnedBy   string `json:"owned_by"`
	IsLoaded  bool   `json:"is_loaded"`
	Backend   string `json:"backend"` // e.g., "llama.cpp", "openai"
}

// ModelRegistry manages the lifecycle and hot-swapping of models
type ModelRegistry struct {
	mu     sync.RWMutex
	models map[string]*Model
	path   string
}

func NewModelRegistry(path string) *ModelRegistry {
	return &ModelRegistry{
		models: make(map[string]*Model),
		path:   path,
	}
}

func (r *ModelRegistry) LoadModels() {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	// Pre-populate with default local model as requested
	r.models["Qwen2.5-72B-Instruct"] = &Model{
		ID:       "Qwen2.5-72B-Instruct",
		Object:   "model",
		OwnedBy:  "vyrex",
		IsLoaded: true,
		Backend:  "llama.cpp",
	}
	log.Info("Loaded default model: Qwen2.5-72B-Instruct")
}

func handleListModels(w http.ResponseWriter, r *http.Request) {
	registry.mu.RLock()
	defer registry.mu.RUnlock()

	var list []Model
	for _, m := range registry.models {
		list = append(list, *m)
	}

	response := map[string]interface{}{
		"object": "list",
		"data":   list,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

type HotswapRequest struct {
	ModelURL string `json:"model_url"`
}

func handleHotswapModel(w http.ResponseWriter, r *http.Request) {
	var req HotswapRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Infof("Hot-swapping to new model from URL: %s", req.ModelURL)
	
	// Simulate downloading and quantization via llama.cpp
	newModelID := "custom-model-" + req.ModelURL
	
	registry.mu.Lock()
	registry.models[newModelID] = &Model{
		ID:       newModelID,
		Object:   "model",
		OwnedBy:  "vyrex",
		IsLoaded: true,
		Backend:  "llama.cpp",
	}
	registry.mu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":   "success",
		"model_id": newModelID,
	})
}
