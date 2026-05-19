---
layout: post
title: "Sort Algorithms: Priority Queues"
date: 2014-04-19
comments: true
categories: [home, algorithms]
abstract: "Priority Queues is a data type to find the largest M items in a
stream of N items. "
---

> Priority Queues is a data type to find the largest M items in a
stream of N items (Constrict: Not enough memory to store N items). 

#### Why Algorithms ?
* Programs = Data structures + Algorithms  

* Avi Wigderson gives that "Algorithms has becoming a common language for understanding nature, human, and computer" .  Algorithms as computational models are replacing math models in scientific inquiry . People are developing computational models to stimulate what might be happening in nature in order to try to better understand it. Algorithms play an extremely important role in this process .  

#### Introduction
Priority Queues is a data type to find the largest M items in a
stream of N items (Constrict: Not enough memory to store N items).   

#### priority-queue implementation based on the binary heap
Using priority queues is similar to using queues and stacks
but implementing them efficiently is more challenging.  We consider a
classic priority-queue implementation based on the **binary heap**
data structure, where items are kept in an array, subject to certain
ordering constraints that allow for **efficient (log-time)
implementations** of remove the maximum and insert.

We use array representation of a heap-ordered complete binary tree.
Because array implementation **does not waste any space on the usual
pointers** you have in a tree to traverse between parents and
children. The reason is that we're able to **keep this binary tree as
balanced as possible**, we don't need pointers to figure out the parents
and children. we can just read that off directly from the position in
the array.

#### binary heap
The binary heap is that **parent's key no smaller than children's key**, that's (k is the index),
>set a[k] to a[k/2] when we move up the tree
>
>set a[k] to a[2\*k] or a[2\*k+1] when move down the tree 

We can take advantage of the capability to move up and down paths in
the tree without pointers and have guaranteed **logarithmic performance**
because the height of a complete binary tree of size N is lgN.

 
The basic algorithm swim (bottom-up reheapify) moves up the heap until we reach a node with a larger key, or the root.

The function swim(int k) with Java  
``` java
//the parent of the node at position k in a heap is at position k/2
private void swim(int k){
    while(k > 1 && less(k/2, k)){  //the node's key larger than parent's key
        exch(k/2, k);              //exchange the node with its parent
        k = k/2;
    }
}
```

The sink algorithm movs down the heap until we reach a node with both children smaller(or equal,) or the bottom. 

The function sink(int k) with Java  
``` java
//the children of the node at position k in a heap are at positions 2k and 2k+1
private void sink(int k){
    while(2*k <= N){
        int j = 2*k;                    //the children of the node
        if (j < N && less(j, j+1)) j++; //find the smaller children
        if (!less(k, j)) break;
        exch(k, j);                     //swap the node with the smaller children
        k = j;
    }
}
```

The insert algorithm requires no more than 1 + lgN compares, which involving **moving along a path between the root and the bottom of the heap** whose number of links is no more than lgN.

The function insert(key x)

``` java
public void insert(Key x){
    pq[++N] = x;
    swim(N);     //swim up through the heap

}
```

The heap algorithms require no more than 2lgN compares for remove the maximum; The operation involves moving the heap path no more than lgN, and it requires two compares for each node on the path (except at the bottom): one to find the child with larger key, the other to decide whether that child needs to be promoted.

The function delMax()

``` java
public Key delMax(){
    Key max = pq[1]; //the largest key off the top
    exch(1, N--);    //exchange the last one with root
    sink(1);         //sink sown through the heap
    pq[N+1] = null;  //to avoid loitering and help with garbage collection

    return max;
}
```

#### Performance Analysis:
For typical applications that **require a large number of intermixed insert and remove the maximum/min operations** in a large priority queue, the elementary implementations using an ordered array or an unordered array require linear time for one of the operations, a heap-based implementation provides a guarantee that both operations complete in **logarithmic time**.
