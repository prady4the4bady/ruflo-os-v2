def find_element(image_base64: str, description: str) -> dict:
    # In production, this would load YOLO or send the image to LLaVA via Vyrex.
    # We provide a deterministic mock based on description for the smoke test.
    print(f"[Vision Service] Finding element: {description}")
    
    if "terminal" in description.lower():
        return {"found": True, "x": 300, "y": 400, "confidence": 0.88}
    
    return {
        "found": True, 
        "x": 500, 
        "y": 500, 
        "confidence": 0.75
    }
