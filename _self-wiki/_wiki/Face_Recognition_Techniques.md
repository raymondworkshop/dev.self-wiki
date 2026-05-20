---
last_updated: 2024-05-29T12:00:00Z
title: Face Recognition Techniques (Eigenfaces, Fisherfaces, LBPH)
description: A technical breakdown of machine learning approaches used in facial recognition, including Eigenfaces, Fisherfaces, and Local Binary Patterns Histograms.
tags: [type/principle, technology, cognitive_model]
---

> This document synthesizes technical approaches for facial recognition using OpenCV, detailing Eigenfaces, Fisherfaces, and Local Binary Patterns Histograms (LBPH). It covers the underlying mathematical concepts, algorithmic steps, and performance evaluation metrics like ROC and CMC.

## Evolution
- Initial concepts were derived from a raw technical note regarding the implementation of face recognition algorithms. The structure has been formalized to serve as a technical principle document.

## Content

### Approaches to Face Recognition

#### 1. Geometric Feature Extraction
- Marker points (e.g., eyes, ears, nose positions) are used to construct a feature vector based on inter-point distances and angles.

#### 2. Eigenfaces (PCA-based)
- **Concept**: A facial image is treated as a point in a high-dimensional image space. Since high-dimensional data often exhibits correlation, a lower-dimensional subspace captures most of the meaningful information.
- **Algorithm**: Principal Component Analysis (PCA) is used to find the lower-dimensional subspace with maximum variance (relative to the mean).
    - The implementation leverages the fact that an $M \times N$ matrix ($M>N$) has at most $N-1$ non-zero eigenvalues, allowing the use of an $N \times N$ eigenvalue decomposition matrix.
    - The process involves:
        1. PCA computation on the training data.
        2. Projection of test samples into the principal component subspace.
        3. Prediction using the learned subspace and a distance threshold.
- **OpenCV API Usage**: `Ptr<FaceRecognizer> createEigenFaceRecognizer(int num_components, double threshold)`
    - PCA is performed on the data.
    - Feature vectors are obtained by projecting the sample onto the eigenvectors.
    - Prediction uses the learned subspace and compares distances.

#### 3. Fisherfaces
- *(Details not present in the source, but noted as a category.)*

#### 4. Local Binary Patterns Histograms (LBPH)
- **Concept**: This method focuses on extracting local features, resulting in an implicitly low-dimensional representation. LBP is used to summarize local image structure while being robust against variations in illumination, scale, translation, or rotation.
- **Algorithm**:
    1. **LBP Image Calculation**: Each pixel is compared against its neighborhood to generate a local binary pattern.
    2. **Spatial Histogram**: A spatial histogram is generated from the LBP image, where grid sizes ($\text{grid\_x}, \text{grid\_y}$) control the binning.
    3. **Feature Vector**: The resulting spatial histogram serves as the feature vector.
    4. **Prediction**: Comparison between histograms is done using the Chi-square ($\chi^2$) test for distance measurement.
- **OpenCV API Usage**: `Ptr<FaceRecognizer> createLBPHFaceRecognizer(int radius, int neighbors, int grid_x, int grid_y, double threshold)`

### Performance Evaluation
- **Receiver Operating Characteristic (ROC)**: Plots the True Acceptance Rate (TAR) vs. False Acceptance Rate (FAR), illustrating the trade-off between true positive benefits and false positive costs.
- **Cumulative Match Characteristic (CMC)**: Plots the probability of identification against the size of the candidate list ($1:N$), showing how likely a user is to appear in various sized lists.

## Conclusion
The implementation of facial recognition is a multi-faceted problem solvable through geometric feature encoding, dimensionality reduction techniques (Eigenfaces/PCA), or local pattern description (LBPH). Successful deployment requires rigorous performance evaluation using metrics like ROC and CMC to balance acceptance rates against error costs.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Self_Assessment_and_Life_Goals.md]] (Potential connection regarding complex systems)
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/2015-03-06-facerecognition_with_opencv.md]]