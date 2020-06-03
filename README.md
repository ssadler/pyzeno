# pyzeno

This is a tool I am using to debug the zeno (https://github.com/ssadler/zeno) notarizer. It is very much in its infancy. As of now, it will connect to a specified seed node, requests peers from this seed node, connect to each of these peers then continually print out the packets, decoding what it can, it receives from each peer. 

The long term plan for this is to be a tool for metrics and debugging.

Right now it's just a very simple script. If you're interested in using it at this point, it should be pretty self explanatory. I will update this README with better instructions once the project is more mature. 

TODO:
die gracefully
decode each packet type and log all of it's data
detect zeno networking protocol and drop conenction if protocol is violated 
metrics of network timing, missing expected packets, malformed packets, dropped connections
interactive py shell - it does this now with pdb, but it is far from optimal 

Feel free to contribute PRs or suggestions in the issues.
