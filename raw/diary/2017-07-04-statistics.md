---
layout: post
title: "Summary about Probability and Statistics"
date: 2017-07-04
comments: true
categories: [home, algorithms]
abstract: "[updating] Summary about Probability and Statistics"
---

> [updating] A Summary about Probability and Statistics

#### Bayesians

TODO

#### Statistical Inference

-   总体和样本

    -   总体分布是一个概率分布族(因为参数未知)
    -   非参数总体(假定总体有一定的概率分布而并不明确知其道数学形式)
    -   从总体中抽出的**独立随机**的样本

      <br/>

-   由样本推断总体：为解决具体问题而抽样，**样本分布族规定了问题的统计模型(概率分布)**，样本的具体数值推断样本分布中的未知参数。比如 依据样本 $\chi_1, ..., \chi_n$ 对分布 $N(\mu, \sigma^2)$中的参数 $\mu$ 作推断，这个推断的具体内容依据样本 $\chi_1, ..., \chi_n$ 算出一个数作为 $\mu$ 估计值。

      <br/>

-   Frequentist - 极大似然估计方法 (Maximum likelihood estimation) (要求假设的分布函数有参数形式) 是用来估计一个概率模型的参数的一种方法。

    假设总体有分布 $f(\chi;\theta_1,...,\theta_k)$, $\chi_1,...\chi_n$ 为抽出的样本; 當有了結果 $\chi$（样本）时，即在所有由原因 $\theta$ 而产生的可能性中，寻找一个值使这个 $\chi$（样本）的“可能性”最大(即似然程度最大)。

    则有似然函数:

    $$
    L(\theta|\chi_1,...,\chi_n) = f(\chi_1|\theta)f(\chi_2|\theta)...f(\chi_1|\theta) = \prod_{i=1}^n f(\chi_i|\theta)
    $$

    $$
    log(L(θ|\chi_1,...,\chi_n)) = \sum_{i=1}^n {\log(f(\chi_i|\theta))}
    $$

    我们要似然程度最大, 即“极大似然估计”:

    $$
    \hat{\theta} = \mathop {argmax}_{\theta}
    $$

#### Nonparametric statistics

One of the biggest problems with tests like the chi-squared test is that they make a lot
of assumptions about how your data was generated. Often we could figure out that this is
without having to make a bunch of assumptions .

#### reference

-   [Statistical Rethinking: A Bayesian Course with Examples in R and Stan](https://github.com/rmcelreath/statrethinking_winter2019)
-   [Some good "Statistics for programmers" resources](https://jvns.ca/blog/2017/04/17/statistics-for-programmers/)
-   [统计学浅谈](http://episte.math.ntu.edu.tw/articles/mm/mm_03_3_07/index.html)
-   陈希孺的《概率论与数理统计》
