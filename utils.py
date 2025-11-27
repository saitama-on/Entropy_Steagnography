import numpy as np
import cv2

def text_to_bits(text):
    """Convert a string to a string of bits."""
    return ''.join(f"{ord(c):08b}" for c in text)

def bits_to_text(bits):
    """Convert a string of bits back to text."""
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) == 8:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)

def bytes_to_image(file_bytes):
    """Convert uploaded file bytes to an OpenCV image."""
    file_bytes = np.asarray(bytearray(file_bytes), dtype=np.uint8)
    return cv2.imdecode(file_bytes, 1)

def mse(img1, img2):
    """Calculate Mean Squared Error between two images."""
    h, w = img1.shape[:2]
    img2 = cv2.resize(img2, (w, h))
    return np.mean((img1 - img2) ** 2)
