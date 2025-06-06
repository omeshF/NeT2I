# NeT2I - Network to Image

**NeT2I** (Network to Image) is a Python tool for converting structured network traffic data into RGB images that can be used for anomaly detection via Convolutional Neural Networks (CNNs). It supports CSV inputs containing IP addresses, MAC addresses, numeric values, and string fields. These are automatically detected, processed, and encoded into image representations.

---

## 🔍 Key Features

- Converts **CSV-based network traffic** into RGB images  
- Handles **MAC addresses**, **IP addresses**, **integers**, **floats**, and **strings**  
- Encodes numeric data using **IEEE 754 float-to-byte** representation for **lossless recovery**  
- Outputs RGB images for CNN model training or anomaly detection tasks  
- Includes **type detection**, **data normalization**, and **image generation**

---

## 📦 Requirements

- Python 3.9 or later  
- [Pillow](https://pypi.org/project/Pillow/)  
- [NumPy](https://pypi.org/project/numpy/)  
- [Pandas](https://pypi.org/project/pandas/)

Install the dependencies using:

```bash
pip install pillow numpy pandas
```

---

## 🚀 Getting Started

### 1. Prepare Your Data

Place your CSV file in the working directory and rename it to:

```
source_in2.csv
```

Each row in this file should represent one sample of network data. No headers are expected.

---

### 2. Run the Script

```bash
python net2i.py
```

This will:
- Detect and map each column to its correct type (IP, MAC, float, etc.)
- Convert each row into two RGB pixels per float-equivalent value
- Create one `.png` image per row in the `data/` directory
- Generate a `data_types.json` file for decoding and debugging

---

## 🧠 How It Works

- **MAC Addresses** are split into two hexadecimal chunks and treated as large integers.  
- **IP Addresses** are split into four octets, each converted to float.  
- **Integers** are **first cast to float** before encoding to RGB using `struct.pack()`, preserving their IEEE 754 byte format.  
- **Strings** are hashed to integers, then converted to floats and encoded similarly.

Each float is encoded into **two RGB pixels** (6 bytes) to avoid information loss.

---

## 📁 Output Structure

- `data/`: Directory containing all generated RGB images (one per row)  
- `data_types.json`: Contains original and final column types after preprocessing  
- `from_image.csv`: Placeholder file for reverse decoding (optional, not yet included)

---

## 🧪 Example Use Case

Once converted, these RGB images can be fed into CNN models like ResNet, VGG, or custom classifiers for anomaly detection, intrusion detection, or network behavior classification tasks.

---

## 🛠️ Configuration

You can adjust these options at the top of the script:

```python
INPUT_CSV = "source_in2.csv"
OUTPUT_DIR = "data"
IMAGE_SIZE = 150
TYPES_FILE = "data_types.json"
DECODED = "from_image.csv"
```

---

## 💡 Usage Examples

### Basic Usage

```python
import NeT2i.converter as converter

# Simple conversion
results = converter.load_csv('source_in2.csv')
print(f"Generated {results['num_images']} images")
```

### Advanced Usage with Custom Parameters

```python
import NeT2i.converter as converter

# Custom configuration
results = converter.load_csv(
    'source_in2.csv',
    output_dir='my_images',
    image_size=150,
    types_file='my_types.json',
    clean_existing=True
)

# Access results
print(f"Original CSV shape: {results['original_shape']}")
print(f"Detected types: {results['original_types']}")
print(f"Final types after splitting: {results['final_types']}")
```

### Object-Oriented Usage

```python
from NeT2i.converter import NeT2iConverter

# Create converter instance with custom settings
converter = NeT2iConverter(
    output_dir='data_images',
    image_size=150,
    clean_existing=True
)

# Convert multiple files
results1 = converter.load_csv('file1.csv')
results2 = converter.load_csv('file2.csv')
```

---

## 🧾 License

This project is licensed under the [MIT License](LICENSE).

---

## 👥 Authors

- [Omesh Fernando](mailto:omeshf@gmail.com)  
- [Sajid Fadlelseed](mailto:sajidqurashi1@gmail.com)

---

## 🌐 Project Links

- 🔗 [GitHub Repository](https://github.com/omeshF/NeT2I)  
- 🐛 [Report Issues](https://github.com/omeshF/NeT2I/issues)