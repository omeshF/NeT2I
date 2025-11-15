# net2i - Network Data to Image Converter

A Python library for converting network traffic data (CSV format) into
RGB images for machine learning applications, particularly CNNs.\
`net2i` provides **lossless**, **bijective** encoding so that traffic
data can be perfectly reconstructed using the companion tool **i2net**.

net2i is also available as a pypi library
[![PyPI
Version](https://img.shields.io/pypi/v/net2i.svg)](https://pypi.org/project/net2i/)\

[![PyPI
Downloads](https://img.shields.io/pypi/dm/net2i.svg)](https://pypi.org/project/net2i/)

### 🔄 Companion Tool

**Decode net2i images back to CSV:**\
i2net on Github : [i2net](https://github.com/omeshF/I2NeT)

i2net is also available as a pypi library: 
[i2net on PyPI](https://pypi.org/project/i2net/)\
[![i2net
PyPI](https://img.shields.io/pypi/v/i2net.svg)](https://pypi.org/project/i2net/)

------------------------------------------------------------------------

# 🚀 Features

-   🔍 **Automatic IP Version Detection** (IPv4 & IPv6)
-   💎 **Lossless Bijective Encoding** for perfect reconstruction
-   📅 **Smart Timestamp Handling** → expands timestamps into 6
    components
-   🌐 Supports IPs, MACs, floats, integers, strings
-   🧠 **CNN-ready images**
-   📋 **Full type metadata saved** for decoding via i2net
-   ⚙️ Configurable (image size, output directory)
-   🔀 Mixed IPv4 + IPv6 in the same dataset

------------------------------------------------------------------------

# 📦 Installation
### 📥 Install from GitHub

You can install NeT2I directly from the GitHub repository:
``` bash
git clone https://github.com/omeshF/NeT2I.git
cd NeT2I
```

### Via PyPI

``` bash
pip install net2i
```

### Requirements

-   Python 3.9+
-   pandas
-   numpy
-   Pillow
-   dateutil
-   ipaddress (built-in)

------------------------------------------------------------------------

# 🚀 Quick Start

### Basic Usage

``` python
import net2i

results = net2i.encode("network_traffic.csv")
print(f"Generated {results['total_images']} images in '{results['output_dir']}'")
```

### Custom Configuration

``` python
import net2i

results = net2i.encode(
    "firewall_logs.csv",
    output_dir="cnn_training_data",
    image_size=224
)
```

### Global Config

``` python
net2i.set_config(
    output_dir="training_images",
    image_size=150,
    clean_existing=True
)

results = net2i.encode("network_data.csv")
```

------------------------------------------------------------------------

# 📊 Supported Network Data Types

 ## Encoding Summary

| Data Type      | Detection Method   | Encoding Strategy                     | Output Pixels |
|----------------|--------------------|----------------------------------------|---------------|
| IPv4 Address   | Pattern match      | 4 octets → floats                      | 8 px          |
| IPv6 Address   | Pattern match      | 16 bytes + padding                     | 6 px          |
| MAC Address    | Regex              | 6 bytes → floats                       | 4 px          |
| Float/Integer  | Numeric detection  | IEEE-754 encoding                      | 2 px          |
| Timestamp      | Automatic          | Y, M, D, H, M, S (6 components)        | 12 px         |
| String         | Fallback           | Stable hash → float                    | 2 px          |


# 📁 Output Structure

    output_dir/
    ├── ipv4_0.png
    ├── ipv4_1.png
    ├── ipv6_0.png
    ├── ipv6_1.png
    ├── data_types.json
    ├── data_types_ipv6.json
    ├── ipv4_rows.csv
    └── ipv6_rows.csv

------------------------------------------------------------------------

# 🔧 API Reference

### encode(csv_path, \*\*kwargs)

Main function to convert CSV → images.

Returns:

``` python
{
  "input_file": "...",
  "output_dir": "...",
  "image_size": 150,
  "has_ipv4": True,
  "has_ipv6": False,
  "total_images": 1000,
  "ipv4_results": {...},
  "ipv6_results": None
}
```

### Utility Functions

-   `load_csv(path)`
-   `set_config(...)`
-   `show_config()`
-   `reset_config()`
-   `help()`

------------------------------------------------------------------------

# 🧠 Machine Learning Integration

## TensorFlow / Keras

``` python
net2i.set_config(image_size=224, output_dir='training_data')
results = net2i.encode('network_traffic.csv')
```

## PyTorch

``` python
net2i.encode("network_logs.csv", image_size=224)
```

------------------------------------------------------------------------

# 📋 Input Data Format

-   CSV (headers optional)\
-   Mixed datatypes supported\
-   Common formats: IPs, MACs, timestamps, ports, ints, floats, strings

### Example

    12,03/09/2025 22:42:02,2001:0db8:85a3:0000:0000:8a2e:0370:7334,52:54:00:34:65:b2
    11,03/09/2025 22:42:01,192.168.248.159,52:54:00:34:65:b2

------------------------------------------------------------------------

# 🔄 Reverse Decoding with i2net

``` python
import net2i
import i2net.decoder as decoder

net2i.encode("traffic.csv")
decoder.load_data("data", "reconstructed.csv")
```

PyPI pages:
- https://pypi.org/project/net2i/
- https://pypi.org/project/i2net/

------------------------------------------------------------------------

# 🛠️ Technical Overview

-   Load & type-detect CSV\
-   Split IPv4/IPv6\
-   Encode: IEEE-754 floats → RGB pixels\
-   Assemble square images\
-   Save type metadata for decoding

------------------------------------------------------------------------

# 🎯 Image Size Recommendations

  CNN Model    Recommended Size
  ------------ ------------------
  Default      150×150
  ResNet/VGG   224×224
  Inception    299×299

------------------------------------------------------------------------

# 🖥️ CLI Usage

``` bash
python net2i.py network_traffic.csv
python net2i.py firewall_logs.csv cnn_images 224
python net2i.py
```

------------------------------------------------------------------------

# 📚 Citation
Please cite our work

    @article{fernando2025bijective,
      title={Bijective Network-to-Image Encoding for Interpretable CNN-Based Intrusion Detection System},
      author={Fernando, Omesh A. and Spring, Joseph and Xiao, Hannan},
      journal={Network},
      volume={5},
      number={4},
      pages={42},
      year={2025}
    }

------------------------------------------------------------------------

# 👥 Author

**Omesh Fernando**

# 📄 License

MIT License

------------------------------------------------------------------------

# 🔗 Related

-   **i2net (decoder):** https://pypi.org/project/i2net/
-   **Journal Article (2025)** - *Bijective Network-to-Image Encoding
    for Interpretable CNN-Based IDS*

------------------------------------------------------------------------

# 🤝 Contributing

1.  Fork\
2.  Create branch\
3.  Add tests\
4.  Commit\
5.  Push\
6.  Open PR

------------------------------------------------------------------------

# 💬 Support

-   GitHub Issues\
-   `net2i.help()`\
-   `i2net`
