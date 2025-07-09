# net2i - Network Data to Image Converter

A Python library for converting network traffic data (CSV format) into RGB images for machine learning applications, particularly CNNs. net2i uses lossless encoding to preserve all data information while creating CNN-ready image datasets from network traffic logs.

> **🔄 Companion Tool**: Use [i2net](https://github.com/omeshF/I2NeT) to decode images back to CSV format

## 🚀 Features

- **🔍 Automatic IP Version Detection**: Separates IPv4 and IPv6 data automatically  
- **💎 Lossless Data Encoding**: Converts network data to RGB pixels without information loss  
- **🌐 Multiple Data Type Support**: Handles IP addresses, MAC addresses, floats, integers, and strings  
- **🧠 CNN-Ready Output**: Generates images optimized for convolutional neural networks  
- **📋 Type Information Preservation**: Saves encoding metadata for data reconstruction via i2net  
- **⚙️ Configurable Parameters**: Customizable image size and output directories  
- **🔀 Mixed IP Version Support**: Processes IPv4 and IPv6 data in the same dataset  

## 📦 Installation

```bash
pip install pandas numpy pillow
```

**Requirements:**
- Python 3.9+
- pandas
- numpy
- Pillow (PIL)
- ipaddress (built-in)

## 🚀 Quick Start

### Basic Usage
```python
import net2i

# Convert network traffic CSV to images
results = net2i.encode('network_traffic.csv')
print(f"Generated {results['total_images']} images in '{results['output_dir']}'")
```

### With Custom Configuration
```python
import net2i

# Configure for specific CNN requirements
results = net2i.encode(
    'firewall_logs.csv',
    output_dir='cnn_training_data',
    image_size=224  # ResNet/VGG input size
)
```

### Global Configuration
```python
import net2i

# Set global defaults
net2i.set_config(
    output_dir='training_images',
    image_size=150,
    clean_existing=True
)

# Use configured settings
results = net2i.encode('network_data.csv')
```

## 📊 Supported Network Data Types

| Data Type | Detection Method | Encoding Strategy | Output Pixels |
|-----------|------------------|-------------------|----------------|
| **IPv4 Address** | Automatic pattern matching | Split into 4 octets → IEEE 754 encoding | 8 RGB pixels |
| **IPv6 Address** | Automatic pattern matching | 128-bit → 16 bytes + 2 padding | 6 RGB pixels |
| **MAC Address** | Regex: `XX:XX:XX:XX:XX:XX` | Split into 2 hex chunks → float encoding | 4 RGB pixels |
| **Float/Integer** | Numeric detection | Direct IEEE 754 encoding | 2 RGB pixels |
| **String** | Default fallback | Consistent hash → float encoding | 2 RGB pixels |

### Encoding Details
- **Two-Pixel-Per-Float Strategy**: Each float value uses exactly 2 RGB pixels (6 bytes) for lossless IEEE 754 representation  
- **IP Address Decomposition**: IPv4 addresses split into octets, IPv6 addresses use full 128-bit representation  
- **Hash-Based String Encoding**: Strings converted using consistent hashing for reproducible results  

## 🔧 API Reference

### Core Functions

#### `encode(csv_path, **kwargs)`
Main function to convert CSV network data to images.

**Parameters:**
- `csv_path` (str): Path to input CSV file containing network traffic data
- `output_dir` (str, optional): Directory for output images (default: 'data')
- `image_size` (int, optional): Size of square output images (default: 150)

**Returns:**
```python
{
    'input_file': 'network_traffic.csv',
    'output_dir': 'data',
    'image_size': 150,
    'has_ipv4': True,
    'has_ipv6': False,
    'total_images': 1000,
    'ipv4_results': {...},
    'ipv6_results': None
}
```

#### `load_csv(csv_path)`
Load and validate network traffic CSV file.

#### `set_config(**kwargs)`
Configure global settings for all operations.

**Configuration Options:**
- `output_dir`: Output directory for generated images
- `image_size`: Image dimensions (width × height) - tune for your CNN architecture
- `types_file`: JSON file for IPv4 type information ('data_types.json')
- `types_file_ipv6`: JSON file for IPv6 type information ('data_types_ipv6.json')
- `clean_existing`: Clean existing files before processing (default: True)

### Utility Functions
- `show_config()`: Display current configuration
- `reset_config()`: Reset to default settings
- `help()`: Show detailed usage examples

## 📁 Output Structure

### Generated Files
```
output_dir/
├── ipv4_0.png              
├── ipv4_1.png
├── ipv4_2.png
├── ...
├── ipv6_0.png              
├── ipv6_1.png
├── ...
data_types.json             
data_types_ipv6.json        
ipv4_rows.csv              
ipv6_rows.csv              
```

### Type Information Files
```json
{
  "ip_version": "IPv4",
  "original_types": ["IPv4 Address", "Float", "String"],
  "final_types": ["IPv4 Address", "IPv4 Address", "IPv4 Address", "IPv4 Address", "Float", "String"],
  "encoding_info": {
    "description": "Data type mapping for decoding - IPv4 version",
    "float_encoding": "Each float becomes 2 RGB pixels (6 bytes total)",
    "ipv4_encoding": "IPv4 address split into 4 octets, each becomes 2 RGB pixels"
  },
  "original_columns": 3,
  "final_columns": 6
}
```

## 🧠 Machine Learning Integration

### TensorFlow/Keras Pipeline
```python
import net2i
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

net2i.set_config(image_size=224, output_dir='training_data')
results = net2i.encode('network_traffic.csv')

datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2,
    rotation_range=10,
    width_shift_range=0.1,
    height_shift_range=0.1
)

train_generator = datagen.flow_from_directory(
    'training_data',
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    subset='training'
)

validation_generator = datagen.flow_from_directory(
    'training_data',
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    subset='validation'
)
```

### PyTorch Integration
```python
import net2i
import torch
from torchvision import transforms, datasets
from torch.utils.data import DataLoader

net2i.encode('network_logs.csv', image_size=224)

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

dataset = datasets.ImageFolder('data', transform=transform)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=4)
```

## 📋 Input Data Format

### CSV Structure
- No headers required  
- Mixed data types supported  
- Standard network formats: IPs, MACs, ports, timestamps  

### Example CSV
```csv
12,2001:0db8:85a3:0000:0000:8a2e:0370:7334,52:54:00:34:65:b2,...
11,192.168.248.159,52:54:00:34:65:b2,...
12,192.168.248.159,52:54:00:34:65:b2,...
```

### Sources
- Firewall logs
- IDS/IPS alerts
- Flow records
- Packet capture summaries
- 5G-MEC data
- IoT communications

## 🔄 Integration with i2net

```python
import net2i
results = net2i.encode('original_traffic.csv')

import i2net.decoder as decoder
decoded_results = decoder.load_data('data', 'reconstructed_traffic.csv')
```

## 🛠️ Technical Implementation

1. Load CSV and detect column types  
2. Separate IPv4 and IPv6 rows  
3. Encode each value by type (MAC/IP/float/string)  
4. Use IEEE 754 encoding for floats  
5. Map values to RGB pixels  
6. Assemble square images

## 🎯 Image Size Recommendations

| CNN Architecture | Recommended Size |
|------------------|------------------|
| Default | 150×150 |
| ResNet, VGG | 224×224 |
| Inception | 299×299 |
| Custom | Match your model |

## 🚨 Troubleshooting

- **No IPs detected**: Check your CSV contains valid IPs  
- **Corrupt images**: Set `clean_existing=True`  
- **Memory errors**: Lower image size or batch processing  

## 🖥️ CLI Usage

```bash
python net2i.py network_traffic.csv
python net2i.py firewall_logs.csv cnn_images 224
python net2i.py  # Show help
```

## 📚 Citation

```bibtex
@inproceedings{fernando2023new,
  title={New algorithms for the detection of malicious traffic in 5g-mec},
  author={Fernando, Omesh A and Xiao, Hannan and Spring, Joseph},
  booktitle={2023 IEEE Wireless Communications and Networking Conference (WCNC)},
  pages={1--6},
  year={2023},
  organization={IEEE}
}
```

## 👥 Author

- **Omesh Fernando**

## 📄 License

MIT License

## 🔗 Related

- [i2net](https://github.com/omeshF/I2NeT): Reverse net2i images  
- [IEEE WCNC 2023 Paper](https://ieeexplore.ieee.org/abstract/document/10118803)

## 🤝 Contributing

1. Fork repo  
2. Create a branch  
3. Add tests  
4. Commit  
5. Push  
6. PR  

## 💬 Support

- GitHub Issues  
- `net2i.help()`  
- [i2net](https://github.com/omeshF/I2NeT)

---
**🔄 Tip**: net2i images are lossless and fully reversible with i2net.
