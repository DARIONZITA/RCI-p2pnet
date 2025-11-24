import sys

class Argumentos:
    def __init__(self):
        self.ipServer = "192.168.56.21"
        self.portServer = 58000
        self.lnkport = 8080
        self.neighMx = 5
        self.hopcount = 5

    def parse(self):
        switch = {
            "-s": "ipServer",
            "-p": "portServer",
            "-l": "lnkport",
            "-n": "neighMx",
            "-h": "hopcount"
        }
        for i in range(1, len(sys.argv)):
            if sys.argv[i] in switch:
                setattr(self, switch[sys.argv[i]], sys.argv[i + 1])
        
        # Garantir que são inteiros
        self.portServer = int(self.portServer)
        self.lnkport = int(self.lnkport)
        self.neighMx = int(self.neighMx)
        self.hopcount = int(self.hopcount)
