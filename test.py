import cv2
from skimage.metrics import structural_similarity as ssim

# Function to crop a tile based on coordinates (x, y, width, height)
def crop_tile(image, x, y, w, h):
    return image[y:y+h, x:x+w]

# Function to compare two tiles using SSIM
def compare_tiles(tile1, tile2):
    # Resize to the same size if necessary
    tile1 = cv2.resize(tile1, (tile2.shape[1], tile2.shape[0]))
    
    # Convert to grayscale for comparison
    gray_tile1 = cv2.cvtColor(tile1, cv2.COLOR_BGR2GRAY)
    gray_tile2 = cv2.cvtColor(tile2, cv2.COLOR_BGR2GRAY)

    # Compute SSIM
    score, _ = ssim(gray_tile1, gray_tile2, full=True)
    return score

# Load the image
image = cv2.imread('image.png')

# Crop two tiles (example coordinates)
tile1 = crop_tile(image, 472+0*104, 226 + 5*104, 104, 104)  # Tile 1 coordinates
tile2 = crop_tile(image, 472+0*104, 226 + 6*104, 104, 104)  # Tile 2 coordinates

# Compare the tiles
similarity_score = compare_tiles(tile1, tile2)
print(similarity_score)
