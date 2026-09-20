# Counting pairs

## A1: objects

There are n distinct labeled objects, where n is an integer >=0. A pair consists
of two different objects without an order. Choosing object a then b and choosing
b then a name the same pair. An ordered choice remembers which object came first.

## A2: count and proof

There are n(n-1)/2 unordered pairs. For n>=2 there are n choices of first
object and n-1 remaining choices of second object. Each unordered pair occurs
exactly twice in this count, once in each order. Divide by 2. For n=0 or n=1
there are no pairs and the formula also gives zero. The notation binom(n,2)
denotes this count; no factorial definition is needed here.

## A3: concrete case

For objects A,B,C,D, the six pairs are AB, AC, AD, BC, BD, CD. Ordered choices
include AB and BA separately, giving twelve choices rather than six.
