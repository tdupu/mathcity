# Odd sums, in the order questions arose

## O1: small examples

1=1, 1+3=4, and 1+3+5=9. These suggested squares, but examples alone do not
settle an identity for every n.

## O2: induction calculation

Set S(0)=0. If S(n)=n squared, adding the next odd number 2(n+1)-1=2n+1
gives S(n+1)=n squared+2n+1=(n+1) squared. Induction starting at n=0 proves
S(n)=n squared for every nonnegative integer n. There is no infinite sum.

## O3: notation written later

For a positive integer k, the kth positive odd integer is 2k-1. For an integer
n>=0, S(n) denotes the finite sum of those terms for k=1,...,n. When n=0 the
index set is empty and its sum is defined to be zero. Induction means checking
n=0 and showing that truth at any nonnegative n implies truth at n+1.
