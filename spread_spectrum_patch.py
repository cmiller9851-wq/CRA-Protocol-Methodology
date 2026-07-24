import numpy as np
from PIL import Image

def text_to_bits(text):
    """Converts a string to a list of binary bits."""
    bits = []
    for char in text.encode('utf-8'):
        bin_str = bin(char)[2:].zfill(8)
        bits.extend([int(b) for b in bin_str])
    return bits

def bits_to_text(bits):
    """Converts a list of binary bits back to a string."""
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        char_code = int("".join(map(str, byte)), 2)
        if char_code == 0:  # Null terminator indicates end of payload
            break
        chars.append(chr(char_code))
    return "".join(chars)

def encode_payload(image_path, output_path, secret_text, block_size=16, strength=12):
    """
    Encodes text into an image by modulating the brightness of macro blocks.
    
    :param image_path: Path to the cover image.
    :param output_path: Where to save the encoded image.
    :param secret_text: The payload message.
    :param block_size: Size of pixel blocks (larger = more robust to resizing).
    :param strength: Intensity of pixel modulation (higher = more robust, but more visible).
    """
    img = Image.open(image_path).convert('RGB')
    img_arr = np.array(img, dtype=np.int16)
    height, width, channels = img_arr.shape
    
    # Append a null character to mark the end of the data payload
    bits = text_to_bits(secret_text + "\x00")
    
    max_blocks_x = width // block_size
    max_blocks_y = height // block_size
    total_capacity = max_blocks_x * max_blocks_y
    
    if len(bits) > total_capacity:
        raise ValueError(f"Payload too large. Max capacity is {total_capacity} bits. Need larger image or smaller blocks.")
    
    bit_index = 0
    for y in range(max_blocks_y):
        for x in range(max_blocks_x):
            if bit_index >= len(bits):
                break
                
            bit = bits[bit_index]
            
            # Define block boundaries
            y_start, y_end = y * block_size, (y + 1) * block_size
            x_start, x_end = x * block_size, (x + 1) * block_size
            
            # Modulate the Blue channel (the human eye is least sensitive to blue changes)
            block = img_arr[y_start:y_end, x_start:x_end, 2]
            
            # Spread Spectrum: Shift the entire block's average value up or down
            if bit == 1:
                block += strength
            else:
                block -= strength
                
            bit_index += 1
            
        if bit_index >= len(bits):
            break
            
    # Clip values to ensure they stay within valid 0-255 image byte ranges
    img_arr = np.clip(img_arr, 0, 255).astype(np.uint8)
    encoded_img = Image.fromarray(img_arr)
    encoded_img.save(output_path, quality=95) # Save with high quality to minimize initial degradation
    print(f"Successfully encoded {bit_index} bits into {output_path}")

def decode_payload(encoded_image_path, reference_image_path, block_size=16):
    """
    Decodes the text payload by comparing the processed image against the original reference image.
    Because web platforms resize images, the script resizes the reference image to match the target.
    """
    # Load the compressed/processed image
    comp_img = Image.open(encoded_image_path).convert('RGB')
    comp_arr = np.array(comp_img, dtype=np.int16)
    height, width, _ = comp_arr.shape
    
    # Load original reference image and force it to match the exact dimensions of the processed target
    ref_img = Image.open(reference_image_path).convert('RGB').resize((width, height), Image.Resampling.LANCZOS)
    ref_arr = np.array(ref_img, dtype=np.int16)
    
    max_blocks_x = width // block_size
    max_blocks_y = height // block_size
    
    extracted_bits = []
    
    for y in range(max_blocks_y):
        for x in range(max_blocks_x):
            y_start, y_end = y * block_size, (y + 1) * block_size
            x_start, x_end = x * block_size, (x + 1) * block_size
            
            # Calculate the average difference in the Blue channel between target and reference
            comp_block_avg = np.mean(comp_arr[y_start:y_end, x_start:x_end, 2])
            ref_block_avg = np.mean(ref_arr[y_start:y_end, x_start:x_end, 2])
            
            # If target block is brighter than reference, it's a 1. Otherwise, it's a 0.
            if comp_block_avg > ref_block_avg:
                extracted_bits.append(1)
            else:
                extracted_bits.append(0)
                
    # Convert extracted stream back into string characters
    return bits_to_text(extracted_bits)

# ==========================================
# EXECUTION EXAMPLE
# ==========================================
if __name__ == "__main__":
    # 1. Embed the payload into an original source image
    payload_message = "TELEMETRY_ID_99281_LAT_40.7128_LON_74.0060"
    encode_payload("input_original.png", "encoded_output.png", payload_message, block_size=16, strength=15)
    
    # --- SIMULATE WEB PLATFORM TAMPERING ---
    # We open the encoded file, resize it down, and compress it into a lossy JPEG to mimic a server pipeline
    tampered = Image.open("encoded_output.png")
    tampered = tampered.resize((tampered.width // 2, tampered.height // 2), Image.Resampling.LANCZOS)
    tampered.save("server_processed_tensor.jpg", "JPEG", quality=75)
    # ---------------------------------------
    
    # 2. Extract payload from the degraded/resized server image using the baseline reference image
    try:
        decoded_message = decode_payload("server_processed_tensor.jpg", "input_original.png", block_size=8) 
        # Note: If the image was shrunk by 50%, block_size drops from 16 to 8 during decoding.
        print("\nExtracted Payload Materializes:")
        print(f"--> {decoded_message}")
    except Exception as e:
        print(f"Decoding failed: {e}")
