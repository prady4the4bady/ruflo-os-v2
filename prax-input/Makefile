CC=gcc
CFLAGS=-Wall -Wextra -O2 -Iinclude $(shell pkg-config --cflags libsystemd gio-2.0 x11 xtst)
LDFLAGS=$(shell pkg-config --libs libsystemd gio-2.0 x11 xtst)

SRC_DIR=src
OBJ_DIR=obj

SOURCES=$(wildcard $(SRC_DIR)/*.c)
OBJECTS=$(patsubst $(SRC_DIR)/%.c, $(OBJ_DIR)/%.o, $(SOURCES))

TARGET=prady-input-daemon

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(OBJECTS) -o $@ $(LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

clean:
	rm -rf $(OBJ_DIR) $(TARGET)

.PHONY: all clean
