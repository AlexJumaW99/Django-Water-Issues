import requests
import os
import time

def download_all_portraits_alternative():
    """
    Downloads 155 real, unique portrait images using the Picsum Photos
    service and saves them sequentially.
    """
    # Create the directory if it doesn't exist
    output_folder = "dummy_user_profile_pics"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print("Starting download of 155 profile pictures using Picsum Photos...")

    # Loop to download images from user9.jpg to user163.jpg
    for i in range(9, 164):
        # This URL provides a random 500x500 image from Picsum Photos.
        # We add a unique query parameter to prevent caching and get a new image.
        image_url = f"https://picsum.photos/500/500?random={i}"
        
        try:
            # The requests library will get the actual image
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()  # Checks if the download was successful

            # Define the path to save the new image
            file_path = os.path.join(output_folder, f"user{i}.jpg")

            # Save the downloaded image to the file
            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"Successfully downloaded and saved: {file_path}")

        except requests.exceptions.RequestException as e:
            print(f"Failed to download image for user{i}. Error: {e}")
        
        # A small delay to be respectful to the free API service
        time.sleep(0.5)

    print("\nDownload complete! All 155 images have been processed.")

if __name__ == "__main__":
    download_all_portraits_alternative()