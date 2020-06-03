# pyzeno

This is a tool I am using to debug the zeno (https://github.com/ssadler/zeno) notarizer. It is very much in its infancy. As of now, it will connect to a specified seed node, requests peers from this seed node, connect to each of these peers then continually print out the packets, decoding what it can, it receives from each peer. 

The long term plan for this is to be a tool for metrics and debugging.

Right now it's just a very simple script. If you're interested in using it at this point, it should be pretty self explanatory. I will update this README with better instructions once the project is more mature. 

If you're running this alongside a haskell zeno instance, comment `peers = GetPeers(seed, py_port)` and define the peer list manually. Zeno can by design only handle one peer from the same IP. An exception to this is `127.0.0.1`, so you can connect to yourself without issue. 

Feel free to contribute PRs or suggestions in the issues.
