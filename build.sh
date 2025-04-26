# Step 1: Update package list
sudo apt-get update

# Step 2: Install Google Chrome
sudo apt-get install -y google-chrome-stable

# Step 3: Install Chrome dependencies (if needed)
sudo apt-get install -y libx11-dev libx11-xcb-dev libxcb1-dev libxcomposite-dev libxrandr-dev libglu1-mesa libgtk-3-0

# Step 4: Install FFmpeg
sudo apt-get install -y ffmpeg

# Step 5: Install Python dependencies (within your virtual environment)
pip install --upgrade pip  # Ensure pip is up to date
pip install webdriver-manager  # For managing ChromeDriver
pip install ffmpeg  # If you're using Python bindings for ffmpeg

# Optional: Install other necessary Python packages, if needed
pip install requests python-dotenv packaging

# Step 6: Start the Streamlit app (assuming your Streamlit code is set up properly)
streamlit run your_streamlit_app.py  # Replace with your Streamlit app script

# Check Streamlit app URL
# Local: http://localhost:10000
# Network: http://10.204.93.8:10000
# External: http://44.233.151.27:10000
