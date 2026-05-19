---
last_updated: 2024-07-11T00:00:00Z
title: 顔识别技术原理 (Face Recognition Principles)
description: 本文件详细记录了使用OpenCV等工具进行面部识别的几种核心算法，包括几何特征向量、特征脸（Eigenfaces）、局部二值模式（LBPH）等，并讨论了性能评估指标。
tags: [#type/evolution, technology, computer-vision, algorithm, principle]
---
# 顔识别技术原理

本文件系统地记录了面部识别任务中几种关键的算法实现方法，它们都旨在将高维度的图像数据降维并转化为可比对的特征向量，从而实现身份的快速匹配。

## 核心算法与方法 (Core Algorithms and Approaches)

### 1. 几何特征向量 (Geometric Feature)
*   **方法**: 利用关键标记点（如眼睛、耳朵、鼻子等的位置）来构建特征向量，这些向量由点之间的距离和角度构成。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。

### 2. 特征脸 (Eigenfaces)
*   **原理**: 认为一张面部图像是一个高维图像空间中的一个点。通过主成分分析（PCA），可以找到一个低维子空间，该子空间能用最少的维度来描述数据中最大的信息量（最大方差）。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。
*   **PCA 应用**: PCA算法用于找到具有最大方差的低维子空间，从而将高维数据降维到低维表示。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。
*   **OpenCV API**: 使用 `Ptr<FaceRecognizer> createEigenFaceRecognizer(int num_components, double threshold)` 等API进行实现，其中 `num_components` 控制保留的主成分数量。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。

### 3. 局部二值模式直方图 (Local Binary Patterns Histograms - LBPH)
*   **原理**: 该方法侧重于提取图像的局部特征，使其对光照变化具有一定的鲁棒性。它通过比较每个像素与其邻域像素来总结局部结构，从而生成一个低维度的局部描述。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。
*   **实现**: 使用 `elbp` 函数生成 LBP 图像，然后通过 `spatial_histogram` 获得空间直方图，该直方图即为特征向量。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。
*   **距离度量**: 在预测阶段，使用 $\chi^2$ 检验（Chi-square test）来衡量特征向量之间的距离。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。

## 性能评估指标 (Performance Metrics)
*   **ROC (Receiver Operating Characteristic)**: 在真接受率（TAR）和错误接受率（FAR）的二维空间中描绘了识别的相对权衡，用于评估分类器的性能。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。
*   **CMC (Cumulative Match Characteristic)**: 绘制了识别概率与候选列表大小的关系图，展示了给定用户出现在不同大小候选列表中的概率。(Source: [[raw/diary/2015-03-06-facerecognition_with_opencv.md]])。

## Evolution
早期的记录是关于算法的初步概念化，后期的记录则提供了具体的、可操作的实现细节，包括使用PCA进行降维和使用LBPH进行局部特征提取，使理论概念落地于工程实践。















































## Backlinks
<!-- BEGIN BACKLINKS -->
- **Contradicts**: [[Self-Hub]]
<!-- END BACKLINKS -->

## sources
- [[raw/diary/2015-03-06-facerecognition_with_opencv.md]]