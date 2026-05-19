---
layout: post
title: "Search Algorithms: Binary Search Trees"
date: 2014-05-25
comments: true
categories: [home, algorithms]
abstract: "Binary search trees (BST) combines the flexibility of insertion in a
linked list with the efficiency of search in an ordered array."
---

#### Searching Algorithm - BST

Binary search trees (BST) combines the flexibility of insertion in a
linked list (using two links per node leads to an efficient
implementation) with the efficiency of search in an ordered array.

BST is a binary tree in symmetric order. A binary tree either either
or two disjoint binary trees. Symmetric order means that each node's
key is larger than all keys in its left subtree, and smaller than all
keys in its right subtree.

A Node is comprised of four fields: a key and a value; a reference to
the left (smaller keys) and right subtree (larger keys).

```java
private class Node {

        private Key key;
        private Value val;
        private Node left;  // the left link points to a BST for items with smaller keys
        private Node right;  // the right link points to a BST for items with larger keys

        public Node (Key key, Value val){
           this.key = key;
           this.val = val;
        }

 }
```

#### The Implementation with Java:

The search use the recursive algorithm to search for a key, the function get()

```java
public void get (Key key){

    return get(root, key);  //starting with the root of the tree

}

private Value get(Node x, Key key){

    if(x == null) return null;

    int cmp = key.compareTo(x.key);
    if(cmp < 0)
        return get(x.left, key);
    else if (cmp > 0)
        return get(x.right, key);
    else
        return x.val;

}
```

The insert put key-value pair into BST, if key already exists, update
with new value, the function put()

```java
public void put(Key key, Value val){

    put(root, key, val);

}

private Node put(Node x, Key key, Value val){

    if (x == null)
        return new Node(key, val);

    int cmp = key.compareTo(x.key);
    if(cmp < 0)
        //x.left is null, after new Node, put this ref to the new node into x.left
        x.left = put(x.left, key, val);
    if(cmp > 0)
        x.right = put(x.right, key, val);
    else
        x.val = val;

    return x;

}
```

#### Performance Analysis:

The running times depend on the shapes of the trees, which depends on the **order in which the
keys come in (insert)**. (If the key is inserted in natural order, this is no difference from
linked list).

**Binary search trees correspond exactly to Quicksort partitioning**. In
the binary search trees, we have a root, and everybody smaller to the
left, and everybody larger to the right. In the Quicksort
partitioning, after the random shuffling, we have the partitioning
element and then we process everybody to the left independently of
everybody to the right, so, if N **distinct keys** are inserted into a BST
**in random order**, the expected number of compares for a
search/insert is **~2lnN(about 1.39lgN) on the average**.

But there's problem that the actual worst
case height if the keys come in in order and reverse order and other
natural orders (the worst tree shape), that the time could be proportional to ~N.

#### Searching Algorithm - red-black BST

#### Searching Algorithm - hash table

-   References:
    -   [Binary Search Trees](http://algs4.cs.princeton.edu/32bst/)
