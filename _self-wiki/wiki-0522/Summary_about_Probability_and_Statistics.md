---
title: Summary about Probability and Statistics
last_updated: '2026-05-26T17:22:47.751660'
description: A foundational review of statistical theory, covering the relationship
  between population distributions, independent random samples, and the process of
  inferring population parameters from sample data.
level: 1
tags:
- MLE
- topic/statistics
- methodology
- type/principle
alias: Summary about Probability and Statistics
---

> This entry outlines the core concepts of statistical inference, contrasting Bayesian approaches with the Frequentist paradigm. It details the Maximum Likelihood Estimation (MLE) method, where a parameter $\theta$ is estimated by maximizing the likelihood function $L(\theta|\chi)$ given the observed sample $\chi$.



### Distillation (2026-05-26) - source: [[../raw/diary/2017-07-04-statistics.md]]
## Summary about Probability and Statistics

### Statistical Inference

- **Population vs. Sample**: The population distribution is a probability distribution family (since its parameter is unknown). Samples drawn from this population must be independent random variables.

- **Inference**: The sample distribution dictates the statistical model used to estimate unknown population parameters from observed sample values. For example, using $\chi_1, ..., \chi_n$ to estimate the mean $\mu$ of a Normal distribution $N(\mu, \sigma^2)$.

### Frequentist Approach: Maximum Likelihood Estimation (MLE)

MLE is a method to estimate a probability model's parameters, assuming the underlying distribution function has a parameter form.

Given a population distribution $f(\chi;\theta_1,...,\theta_k)$ and a sample $\chi_1,...,\chi_n$, the goal is to find the parameter value $\theta$ that maximizes the probability of observing $\chi$.

The Likelihood Function is defined as:
$$L(\theta|\chi_1,...,\chi_n) = f(\chi_1|\theta)f(\chi_2|\theta)...f(\chi_n|\theta) = \prod_{i=1}^n f(\chi_i|\theta)$$

To find the MLE estimate $\hat{\theta}$, we maximize the log-likelihood:
$$\hat{\theta} = \mathop {argmax}_{\theta} \left( \sum_{i=1}^n \log(f(\chi_i|\theta)) \right)$$

### Nonparametric Statistics

Nonparametric tests, such as the chi-squared test, are valuable because they can often provide meaningful conclusions without imposing strong assumptions about the underlying data generation process.


## Evolution
- 2026-05-26: Distilled from raw source [[../raw/diary/2017-07-04-statistics.md]].

## Backlinks


## Sources
- [[../raw/diary/2017-07-04-statistics.md]]
