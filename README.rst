===============================
Random Number Oracle
===============================

Introduction
------------

This is the Random Number Oracle, forked from pyethapp_.

Detailed (unfinished) description can be found here RandomNumberOracle_.

More documentation to come soon...

.. _RandomNumberOracle: https://github.com/ConsenSys/randnums/wiki/Random-Number-Oracle
.. _pyethapp: http://github.com/ethereum/pyethapp


Running
------------
In order to run this app and connect to consensys testnet you need to change your bootstrap 
node in the file ~/.config/pyethapp/config.yaml. You can just append the following 
lines to your file:

```
discovery:
  bootstrap_nodes: ['enode://a0c564c380ea000dde17e6ed7075655959df8ac06e779fb62e13f09725458599321f483050d8481d7d85e2ce2f0e000deb1cc1efe0307cd3d7b655474844d2d2@52.10.133.51:30301']

```

Status
------

RNOService has just some method definition. 



