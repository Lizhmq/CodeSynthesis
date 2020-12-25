from abc import get_cache_token


def getSynFunExpr(bmExpr):
    SynFunExpr = ""
    for expr in bmExpr:
        if len(expr) == 0:
            continue
        elif expr[0] == 'synth-fun':
            SynFunExpr = expr
    return SynFunExpr

def hasIte(prodRule):
    for rule in prodRule:
        for lst in rule[2]:
            if isinstance(lst, list) and lst[0] == "ite":
                return True
    return False

def getName(bmExpr):
    for expr in bmExpr:
        if expr[0] == "synth-fun":
            return expr[1]
    return None


def parseArglist(lst, funcname):
    pass

def getCandidates(bmExpr):
    def getc(expr, funcname):
        if not(isinstance(expr, list) or isinstance(expr, tuple)):
            return []
        if expr[0] in ["=", ">=", "<="]:
            expr1, expr2 = expr[1], expr[2]
            if not isinstance(expr1, list):
                expr1, expr2 = expr2, expr1
            if not isinstance(expr1, list):
                return []
            if type(expr2) not in [str, int]:
                return []
            args = parseArglist(expr1, funcname)

    
    ret = []
    funcname = getName(bmExpr)
    for expr in bmExpr:
        if not isinstance(expr, list):
            continue
        if len(expr) < 1 or expr[0] != "constraint":
            continue
        curcands = getc(expr[1:], funcname)
        ret += curcands
    return ret

def Solver(bmExpr):
    candidates = getCandidates(bmExpr)