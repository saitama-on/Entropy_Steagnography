import streamlit as st
import cv2
import numpy as np
from io import BytesIO

# Import our local modules
import logic
import utils

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Entropy Watermarker",
    page_icon="🔐",
    layout="wide"
)

st.title("🔐 Entropy-Based Image Steganography")
st.markdown("""
**Securely hide text inside image texture.** This tool calculates the entropy (chaos) of an image and hides data only in the noisy parts, 
making the watermark invisible to the human eye.
""")

# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["📤 Embed Watermark", "📥 Extract Watermark", "🔍 Analysis"])

# ==========================================
# TAB 1: EMBEDDING
# ==========================================
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Input Data")
        uploaded_file = st.file_uploader("Upload Cover Image", type=['jpg', 'jpeg', 'png'])
        
        # input selection for secret message
        input_method = st.radio("Message Source", ["Type Message", "Upload Text File"], horizontal=True)
        
        secret_text = ""
        if input_method == "Type Message":
            secret_text = st.text_area("Secret Message", "Confidential Data 2025")
        else:
            text_file = st.file_uploader("Upload Secret Text (.txt)", type=['txt'])
            if text_file:
                # Read and decode the uploaded text file
                secret_text = text_file.read().decode("utf-8")
        
        

    if uploaded_file and secret_text:
        # Load image using our utility
        file_bytes = uploaded_file.read()
        img = utils.bytes_to_image(file_bytes)
        
        with col2:
            st.subheader("2. Preview")
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="Original Image", use_container_width=True)

        # Action Button
        if st.button("🔒 Encrypt & Embed"):
            try:
                # Progress bar container
                progress_bar = st.progress(0)
                
                # Call the logic module
                try:
                    watermarked_img, bits_used, total_bits = logic.embed_payload(
                        img, 
                        secret_text, 
                        progress_callback=progress_bar.progress
                    
                    )
                except TypeError:
                    watermarked_img, bits_used, total_bits = logic.embed_payload(
                        img, 
                        secret_text, 
                        progress_callback=progress_bar.progress
                    )
                
                # Clear progress bar
                progress_bar.empty()
                
                # Success Logic
                if bits_used < total_bits:
                    st.warning(f"⚠️ Capacity Reached: Embedded {bits_used}/{total_bits} bits. Image texture was too low.")
                else:
                    st.success(f"✅ Success! Hidden {bits_used} bits in high-entropy regions.")

                # Prepare Download
                is_success, buffer = cv2.imencode(".png", watermarked_img)
                io_buf = BytesIO(buffer)
                
                st.subheader("3. Result")
                st.image(cv2.cvtColor(watermarked_img, cv2.COLOR_BGR2RGB), caption="Watermarked Image", use_container_width=True)
                
                st.download_button(
                    label="💾 Download Watermarked Image (PNG)",
                    data=io_buf,
                    file_name="watermarked_entropy.png",
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")

# ==========================================
# TAB 2: EXTRACTION
# ==========================================
with tab2:
    st.subheader("Decrypt Hidden Message")
    st.info("Upload an image previously watermarked by this tool.")
    
    decode_file = st.file_uploader("Upload Watermarked Image", type=['png', 'jpg'], key="decode_uploader")
    
    if decode_file:
        file_bytes = decode_file.read()
        decode_img = utils.bytes_to_image(file_bytes)
        
        st.image(cv2.cvtColor(decode_img, cv2.COLOR_BGR2RGB), width=300, caption="Uploaded Image")
        
        if st.button("🔓 Extract Message"):
            with st.spinner("Scanning entropy map for hidden bits..."):
                result_text = logic.extract_payload(decode_img)
                
                if "Error" in result_text:
                    st.error(result_text)
                else:
                    st.success("Message Found:")
                    st.code(result_text)

# ==========================================
# TAB 3: ANALYSIS
# ==========================================
with tab3:
    st.subheader("Steganalysis & Visual Difference")
    st.markdown("Compare the Original image with the Watermarked one to ensure the changes are invisible.")
    
    c1, c2 = st.columns(2)
    img1_file = c1.file_uploader("Original Image", type=['png', 'jpg'], key="orig")
    img2_file = c2.file_uploader("Watermarked Image", type=['png', 'jpg'], key="wat")
    
    if img1_file and img2_file:
        # Load images
        im1 = utils.bytes_to_image(img1_file.read())
        im2 = utils.bytes_to_image(img2_file.read())
        
        # Ensure sizes match
        if im1.shape == im2.shape:
            # ---------------------------
            # 1. MSE & DIFF MAP
            # ---------------------------
            mse_val = utils.mse(im1, im2)
            st.metric(label="Mean Squared Error (MSE)", value=f"{mse_val:.6f}", help="Lower is better. 0 means identical.")
            
            # Calculate raw difference for processing
            diff_raw = cv2.absdiff(im1, im2)
            
            # Heatmap Visualization
            if len(diff_raw.shape) == 3:
                diff_gray = cv2.cvtColor(diff_raw, cv2.COLOR_BGR2GRAY)
            else:
                diff_gray = diff_raw

            # Amplify slightly so the heatmap picks it up
            diff_amp = cv2.multiply(diff_gray, 10) 
            heatmap = cv2.applyColorMap(diff_amp, cv2.COLORMAP_JET)
            heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

            st.image(heatmap, caption="Difference Heatmap (Blue=Low, Red=High)", use_container_width=True)

            # ---------------------------
            # 2. EMBEDDING LOCATIONS (Red Spots)
            # ---------------------------
            st.divider()
            st.markdown("### 📍 Payload Distribution")
            st.write("Visualizing exactly which pixels carry the payload.")
            
            col_viz1, col_viz2 = st.columns([1, 3])
            
            
            spot_size = 500
            
            # Create the visualization
            # 1. Create a binary mask of changed pixels
            _, mask = cv2.threshold(diff_gray, 0, 255, cv2.THRESH_BINARY)
            
            # 2. Dilate the mask based on slider (to make spots visible)
            if spot_size > 1:
                kernel = np.ones((spot_size, spot_size), np.uint8)
                mask = cv2.dilate(mask, kernel, iterations=1)
                
            # 3. Prepare background (Grayscale version of original for contrast)
            background = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY) if len(im1.shape) == 3 else im1.copy()
            background = cv2.cvtColor(background, cv2.COLOR_GRAY2BGR) # Convert back to BGR to allow colored drawing
            
            # 4. Paint Red spots ([0, 0, 255] is Red in BGR)
            background[mask == 255] = [0, 0, 255]
            
            st.image(cv2.cvtColor(background, cv2.COLOR_BGR2RGB), caption="Red spots indicate modified pixels", use_container_width=True)

            # ---------------------------
            # 3. BIT PLANE SLICING
            # ---------------------------
            st.divider()
            st.markdown("### 🔬 Bit Plane Slicing")
            st.write("Decomposing the watermarked image into 8 binary layers. **Plane 0 (LSB)** is where data is hidden.")

            if len(im2.shape) == 3:
                img_gray = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)
            else:
                img_gray = im2
            
            c_rows = st.columns(4) + st.columns(4)
            
            for i in range(7, -1, -1):
                bit_plane = ((img_gray >> i) & 1) * 255
                col_index = 7 - i
                with c_rows[col_index]:
                    st.image(bit_plane, caption=f"Bit Plane {i}", clamp=True, use_container_width=True)

            st.info("ℹ️ **Analysis:** Plane 0 (LSB) usually looks like random noise. If you see structured shapes in Plane 0, it indicates hidden data.")

        else:
           st.error("❌ Dimension Mismatch: Images must have the exact same height and width.")