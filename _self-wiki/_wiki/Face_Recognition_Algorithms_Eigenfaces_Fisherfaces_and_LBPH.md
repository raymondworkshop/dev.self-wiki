---
title: 'Face Recognition Algorithms: Eigenfaces, Fisherfaces, and LBPH'
last_updated: '2026-05-20T20:33:41.248772'
description: A technical summary comparing and detailing the implementation of Eigenfaces,
  Fisherfaces, and LBPH algorithms for facial recognition, including performance metrics
  like ROC and CMC.
level: 1
tags:
- technical_review
- topic/computer_vision
- type/synthesis
alias: Summary about Face Recognition with OpenCV
---

> This document outlines several computational approaches for facial recognition using OpenCV, including geometric feature extraction, Eigenfaces (based on PCA), and Local Binary Patterns Histograms (LBPH). Each method relies on dimensionality reduction or local feature encoding to create a unique, comparable feature vector for identification.



### Distillation (2026-05-20) - source: [[../raw/diary/2015-03-06-facerecognition_with_opencv.md]]
## Face Recognition Algorithms

### Geometric Feature
- Marker points (eyes, ears, nose positions) are used to construct the feature vector based on inter-point distances and angles.

### Eigenfaces
- **Concept**: A facial image is treated as a point in a high-dimensional image space, where principal components capture the most significant variance.
- **PCA Application**: Principal Component Analysis (PCA) is used to find the lower-dimensional subspace with maximum variance, effectively decorrelating variables.
- **Implementation Detail**: The Eigenfaces module utilizes PCA to project data onto a reduced subspace, and prediction involves calculating the L2 norm distance to determine the closest class.

### Local Binary Patterns Histograms (LBPH)
- **Concept**: Focuses on extracting local features, making the descriptor robust against illumination variations, scale, and translation.
- **Process**: LBP summarizes local structure by comparing each pixel to its neighborhood. This leads to the calculation of a spatial histogram, which serves as the final feature vector.
- **Prediction**: Identification is achieved by comparing the query histogram against trained histograms using the Chi-square distance metric.

### Performance Evaluation
- **Receiver Operating Characteristic (ROC)**: Plots True Acceptance Rate (TAR) vs. False Acceptance Rate (FAR) to visualize the trade-off between true positive benefits and false positive costs.
- **Cumulative Match Characteristic (CMC)**: Plots identification probability against the size of the candidate list, indicating how quickly a match is found within a ranked list.


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2015-03-06-facerecognition_with_opencv.md]]
