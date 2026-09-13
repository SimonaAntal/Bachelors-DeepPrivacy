# DeepPrivacy

**Intelligent and Secure Steganography for Sensitive Data Protection in Images**

DeepPrivacy is a web application developed as part of my Bachelor's thesis for the reversible anonymization of sensitive information in images.

The application automatically detects sensitive information such as faces and personal data, anonymizes the detected regions, and securely embeds the information required to recover the original content. This combines computer vision, cryptography, steganography, and deep learning into a single privacy-preserving workflow.

## Features

* Automatic face detection using **YOLO**
* Text extraction using **OCR**
* Sensitive data classification using rule-based detection and **Google Gemini**
* Gaussian blur-based visual anonymization
* **AES-256-GCM** encryption of recovery metadata
* **LSB steganography** for embedding encrypted metadata
* Reversible information embedding using **PRIS**
* User authentication using **JWT**
* Personal encrypted image vault
* Image recovery for authorized users

## Technologies

* **Frontend:** Angular
* **Backend:** FastAPI, Python
* **Database:** MongoDB
* **Computer Vision:** OpenCV, YOLO
* **OCR:** EasyOCR
* **Deep Learning:** PyTorch
* **Security:** AES-256-GCM, JWT, LSB steganography
* **Reversible Embedding:** PRIS

## How It Works

1. An image is uploaded to the application.
2. The image is preprocessed and sensitive regions are detected.
3. Detected sensitive information is classified and converted into a binary mask.
4. Sensitive regions are anonymized using pixelation.
5. Recovery metadata is encrypted using AES-256-GCM.
6. The encrypted metadata is embedded into the anonymized image using LSB steganography.
7. The original sensitive content is incorporated using the PRIS reversible neural network.
8. The resulting protected image can be stored in the user's personal vault.
9. Authorized users can recover the original content using the required cryptographic key and embedded information.

## Project Structure

```text
DeepPrivacy/
├── Backend/        # FastAPI application
├── Frontend/       # Angular application
└── INNValidation   # Metrics used for INN validation
```

## Thesis

This project was developed as part of my Bachelor's thesis in Computer Engineering at the **Gheorghe Asachi Technical University of Iași**, Faculty of Automatic Control and Computer Engineering.

**Thesis title:**
*Intelligent and Secure Steganography for Sensitive Data Protection in Images*
