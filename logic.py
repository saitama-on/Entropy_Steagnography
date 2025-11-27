import cv2
import numpy as np
from skimage.filters.rank import entropy
from skimage.morphology import disk
import utils

def calculate_entropy_map(img):
    """
    Calculates the local entropy of an image.
    High entropy = high texture/noise (good for hiding).
    Low entropy = flat areas (bad for hiding).
    """
    # Convert to gray if not already
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # print(img)
    # Normalize to 0-1 range calculation
    gray_uint8 = (gray).astype("uint8")
    
    # Calculate entropy using a disk footprint of radius 5
    return entropy(gray_uint8, disk(5))

def embed_payload(img, text, progress_callback=None):
    """
    Embeds text into the image based on entropy.
    """
    # 1. Prepare Data
    text_bits = utils.text_to_bits(text)
    text_length = len(text_bits)
    
    # Create 32-bit header for length
    length_bits = f"{text_length:032b}"
    full_bitstream = length_bits + text_bits
    total_bits = len(full_bitstream)
    
    # 2. Prepare Image
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) / 255.0
    entropy_map = calculate_entropy_map(gray)
    # print(entropy_map.min())
    norm_entropy = entropy_map / entropy_map.max()
    
    watermarked = img.copy()
    height, width = img.shape[:2]
    
    bit_index = 0
    count = 0
    #arr for positions
    arr = []
    # 3. Embed Loop
    for y in range(height):
        # Update UI progress bar if callback provided
        if progress_callback and y % 10 == 0:
            progress_callback(min(y / height, 1.0))
            
        for x in range(width):
            if bit_index >= total_bits:
                break
            
            count += 1
            # CONDITION: Entropy > 0.5 AND pixel spacing (every 3rd valid pixel)
            if norm_entropy[y, x] >= 0 and count % 2 == 0:
                bit = int(full_bitstream[bit_index])
                arr.append([x,y])
                # LSB Logic: Clear last bit, then OR with new bit
                # We use the Blue channel (index 0)
                watermarked[y, x, 0] = (watermarked[y, x, 0] & 0xFE) | bit
                bit_index += 1
        
        if bit_index >= total_bits:
            break
    print(width, height)
    for item in arr:
        print(entropy_map[item[1]][item[0]])
    # print("ARRAY : ",arr, "\nentropy :" , norm_entropy[17][183] , "\nImage : " , gray[17][183])
    return watermarked, bit_index, total_bits

def extract_payload(watermarked_img):
    """
    Scans the image for the 32-bit header, then extracts the message.
    """
    extracted_bits = []
    
    gray = cv2.cvtColor(watermarked_img, cv2.COLOR_BGR2GRAY) / 255.0
    entropy_map = calculate_entropy_map(gray)
    norm_entropy = entropy_map / entropy_map.max()
    
    height, width = watermarked_img.shape[:2]
    count = 0
    
    # State tracking
    target_length = 32 # Start looking for header
    seeking_header = True
    
    for y in range(height):
        for x in range(width):
            
            count += 1
            if norm_entropy[y, x] >=0  and count % 2 == 0:
                # Extract LSB
                bit = watermarked_img[y, x, 0] & 1
                extracted_bits.append(str(bit))
                
                # Check Header
                if seeking_header and len(extracted_bits) == 32:
                    header_str = "".join(extracted_bits)
                    try:
                        data_length = int(header_str, 2)
                        target_length = 32 + data_length
                        seeking_header = False
                    except:
                        return "Error: Header corruption"

                # Check Body
                if len(extracted_bits) >= target_length:
                    full_bitstring = "".join(extracted_bits)
                    # Remove first 32 bits (header)
                    text_bits = full_bitstring[32:] 
                    return utils.bits_to_text(text_bits)
    
    return "Error: End of image reached before message end."
