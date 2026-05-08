---
layout: post
title: "About Priority Queue"
date: 2015-08-04
categories: [algorithms]
abstract: "About Priority Queue"
---

#### Stack: FILO (first in, last out) [1]

-   Stored in computer RAM
-   stack grows and shrinks as functions push and pop local variables;
    Variables are allocated and freed automatically .
-   CPU manage the memory, reading from and writing to stack variables is very fast

#### Heap [1]

-   Stored in computer RAM
-   heap variables are essentially global in scope.
-   Heap memory is slightly slower to be read from and written to,
    because one has to use pointers to access memory on the heap.
-   If we need variables like arrays and structs that can change size dynamically,
    then we will likely need to allocate them on the heap.

#### queue : FIFO

#### stack : FILO (first in, last out)

#### Priority Queue

-   The case
    -   We collect a set of items, then process the one with the largest key, **then perhaps collect more items**,
        then process the one with the current largest key.

    -   a collection in which items can be added at any time, but the only item that can be removed is the one
        with the **highest priority**.
-   The implementations

    -   unordered array/linked-list:

        -   To insert: push in the stack. O(1)
        -   To remove the max: exchange the MAX with the item at the end, and then delete that one. o(n)

    -   ordered array/linked-list:

        -   for insert to move larger entries on the right position,thus keeping the keys in the order array. o(n)
        -   The MAX is always at the end. O(1)

    -   **binary heap** [2]

        -   a binary tree is heap-ordered if the key in each node >= the keys in the node's two children [3].
        -   To insert: **exchanging the node with its parent** to restore the heap condition
        -   To remove:

            -   take the key off the top;
            -   put the item at the end of the heap to the top,
            -   and then sink through the heap with the key to restore the heap condition

        -   In a heap, the highest (or lowest) priority item is always stored **at the root**, hence the name "heap".
            A heap is not a sorted structure and can be regarded as **partially ordered** . There is no particular
            relationship among ndoes on any given level, even among the siblings [4].

        -   A heap is useful data structure when we need to **remove the object with the highest (or lowest) priority**.

        -   O(logN)

[1]: http://gribblelab.org/CBootcamp/7_Memory_Stack_vs_Heap.html "stack and heap"
[2]: http://cs.lmu.edu/~ray/notes/pqueues/ "priority queue"
[3]: http://algs4.cs.princeton.edu/24pq/ "Priority Queues"
[4]: http://www.cs.cmu.edu/~adamchik/15-121/lectures/Binary%20Heaps/heaps.html "priority queues"
