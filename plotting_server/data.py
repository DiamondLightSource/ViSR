import numpy as np


def process_image(image: np.ndarray) -> dict:
    """
    Divide the image into 3 parts, compute sums for each part, and store in a dictionary.
    """
    h, w = image.shape[1], image.shape[2]  # Get height and width of each 2D slice
    segment_height = h // 3

    # Divide image into three parts along the height dimension
    r_sum = np.sum(image[:, :segment_height, :])
    g_sum = np.sum(image[:, segment_height:2 * segment_height, :])
    b_sum = np.sum(image[:, 2 * segment_height:, :])

    # Store results in a dictionary
    return {"r": r_sum, "g": g_sum, "b": b_sum, "total": r_sum + g_sum + b_sum}

def process_and_append(image: np.ndarray, stats_array: list) -> np.ndarray:
    """
    Process a new image, append its stats to the stats array, and calculate the variance array.
    """
    # Process the new image
    stats = process_image(image)
    stats_array.append(stats)

    # Extract r, g, b values from all dictionaries in the stats array
    r_values = np.array([d["r"] for d in stats_array])
    g_values = np.array([d["g"] for d in stats_array])
    b_values = np.array([d["b"] for d in stats_array])

    # Calculate min and max for r, g, b
    r_min, r_max = np.min(r_values), np.max(r_values)
    g_min, g_max = np.min(g_values), np.max(g_values)
    b_min, b_max = np.min(b_values), np.max(b_values)

    # Compute variance (max - min) normalized by max
    variance_array = np.array([
        (r_max - r_min) / r_max if r_max != 0 else 0,
        (g_max - g_min) / g_max if g_max != 0 else 0,
        (b_max - b_min) / b_max if b_max != 0 else 0,
    ])

    return variance_array

# Example usage:
if __name__ == "__main__":
    # Mock data: Create a 4x1216x1936 array filled with ones for testing
    images = np.ones((4, 1216, 1936), dtype=np.uint8)

    # Initialize stats array
    stats_array = []

    # Process the initial image
    process_and_append(images, stats_array)

    # Example: Process another image (you can modify this image as needed)
    new_image = np.ones((4, 1216, 1936), dtype=np.uint8) * 2  # Example of a different image
    variance = process_and_append(new_image, stats_array)

    # Output the variance array
    print("Variance array:", variance)

    # Output the stats array for reference
    print("Stats array:", stats_array)
