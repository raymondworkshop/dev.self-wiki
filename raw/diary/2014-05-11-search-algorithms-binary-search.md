---
layout: post
title: "Search Algorithms: Binary Search"
date: 2014-05-11
comments: true
categories: [home, algorithms]
abstract: "A symbol table is a data structure for key-value pairs. Binary search in an ordered array can implement the symbol table API. "
---

### Introduction
A symbol table is a data structure for **key-value pairs** that supports two operations: insert (put) a new pair into the table and search for (get) the value associated with a given key .

Binary search in an ordered array can implement the symbol table API. The underlying data structure is two parallel array, **with the keys kept in order**.

### The Implementation  with Java  
For get(), the rank() (returns the number of keys) tells us precisely where the key is to be found;


```  java
//return the value associated with the given key, or null
public Value get(Key key){
   int i = rank(key); //return the number of keys in the table
   if(i < N && keys[i].compareTo(key) == 0)
       return vals[i];

   return null;
}
```

```  java 
//return the number of keys in the table that are smaller than given key
public int rank(Key key){
    int lo = 0, hi = N-1;
    while(lo <= hi){
        int m = lo + (hi - lo) / 2;
        int cmp = key.compareTo(keys[m]);

        if (cmp < 0) hi = m - 1;
        else if (cmp > 0) lo = m + 1;
        else return m;
    }

    return lo;
}
``` 


and for put(), the rank tells where to update the value .


``` java
//search for key, update value if found, grow table if new
public void put(Key key, Value val){
    int i = rank(key); //where to update the value

    // key is already in table
    if (i < N && keys[i].compareTo(key) == 0){
         vals[i] = val;
         return;
     }

    // insert new key-value pair
    if (N == keys.length) resize(2*keys.length);

    for (int j = N; j > i; j--)  {
         keys[j] = keys[j-1];
         vals[j] = vals[j-1];
    }

    keys[i] = key;
    vals[i] = val;
    N++;
 }
```


### Performance Analysis

The reason that we **keep keys in an ordered array** is so that we can use **array indexing to dramatically reduce the number of compares required for each search using the known as binary search** ( **can auto calculate the related mid value based on array index**).  

Binary search in an ordered array with N keys uses no more than **lgN + 1** compares for a search; and Inserting a new key into an ordered array uses **~2N array accesses** in the worst case (**e.g. move the array entirely, line 14~16**), so inserting N keys into an initially empty table uses **~$N^2$ array accesses** in the worst case.  

See the table:

|    Algorithm       |  Worst-case-search    |  Worst-case-insert  |
|    :---:           |      :----:           |       :----:        |     
| sequential search  |         N             |          N          |
|   binary search    |        $lgN$          |         2N          |  


### In Summary  
For a **static table** (with no insert operations allowed), it is **worthwhile to initialize and sort the table**.

Still, binary search is infeasible for use in many other applications. For example,it fails because **searches and inserts are intermixed and the table size is too large** . As typical modern search clients require symbole tables that can support fast implementations of both search and insert. The means we have to devise algorithms and data structures that achieve logarithmic performance for both search and insert. To **support efficient insertion**, it seems that we need a **linked structure**. But a singly linked list forecloses the use of binary search, because **the efficiency of binary search depends on the ability to get to the middle of any subarray quickly via indexing**.

To combine the efficiency of binary search with the flexibility of linked structures, we need more complicated data structure. That are **binary search trees and hash tables** .

### References:  
  * [Elementary Symbol Tables](http://algs4.cs.princeton.edu/31elementary/)
