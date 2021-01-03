from copy import deepcopy as cp
import functools
import translator


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

def getSynth(bmExpr):
    for expr in bmExpr:
        if expr[0] == "synth-fun":
            return expr
    return None

def parseArglist(lst, funcname):
    if not isinstance(lst, list):
        return []
    if lst[0] == funcname:
        return lst[1:]

def getAllStr(expr):
    if isinstance(expr, tuple) and expr[1].isdigit():
        return [str(expr[1])]
    if isinstance(expr, str):
        return [expr]
    ret = []
    if isinstance(expr, list):
        for val in expr:
            ret += getAllStr(val)
    return ret

def List2Tuple(lst, arglist):
    if isinstance(lst, list) or isinstance(lst, tuple):
        return tuple(List2Tuple(i, arglist) for i in lst)
    assert(isinstance(lst, str))
    if lst in arglist:
        return "arg" + str(arglist.index(lst))
    return lst

def getCandidates(bmExpr):
    def getc(expr, funcname):
        if not(isinstance(expr, list) or isinstance(expr, tuple)):
            return []
        if len(expr) == 1:
            return getc(expr[0], funcname)
        if expr[0] in ["=", ">=", "<="]:
            expr1, expr2 = expr[1], expr[2]
            if not isinstance(expr1, list):
                expr1, expr2 = expr2, expr1
            if not isinstance(expr1, list):
                return []
            if type(expr2) not in [str, tuple, list]:
                return []
            if isinstance(expr2, tuple) and isinstance(expr2[1], int):
                return [expr2[1]]       # assume all int reachable(not correct)
            arglist = parseArglist(expr1, funcname)
            args = arglist + ["+", "-", "*"]
            if expr2 in args:
                return ["arg" + str(args.index(expr2))]
            values = getAllStr(expr2)
            ins = [val in args for val in values]
            isAvail = functools.reduce(lambda x, y: x and y, ins, True)
            if isAvail:
                return [List2Tuple(expr2, arglist)]
            return []
        res = []
        for exprs in expr:
            res += getc(exprs, funcname)
        return res
    
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

def getConstraints(bmExpr):
    ret = []
    for expr in bmExpr:
        if not isinstance(expr, list):
            continue
        if len(expr) < 1 or expr[0] != "constraint":
            continue
        ret.append(expr)
    return ret

def getVarlist(bmExpr):
    ret = []
    for expr in bmExpr:
        if isinstance(expr, list) and expr[0] == "declare-var":
            ret.append(expr[1])
    return ret

def generateTestcase(varlist, withmax=False):
    k = len(varlist)
    ret = []
    tmp = [0] * k
    if withmax:
        for i in range(k):
            for j in range(k):
                if j == i:
                    continue
                tmp[i] = 2
                tmp[j] = 1
                dic = {varlist[t] : tmp[t] for t in range(k)}
                ret.append(dic)
                tmp[i] = 2
                tmp[j] = 2
                dic = {varlist[t] : tmp[t] for t in range(k)}
                ret.append(dic)
                tmp[i] = tmp[j] = 0
        for i in range(k):
            tmp[i] = 2
            dic = {varlist[t] : tmp[t] for t in range(k)}
            ret.append(dic)
            tmp[i] = 0
    for i in range(k - 1):
        tmp[i] = i * 2
    for j in range(k):
        if j == k - 1:
            tmp[k - 1] = tmp[k - 2] + 1
        else:
            tmp[k - 1] = tmp[j] - 1
        dic = {varlist[t] : tmp[t] for t in range(k)}
        ret.append(dic)
    return ret

def constraintEval(infoDict, constraint, testcase, funcdic):
    if isinstance(constraint, tuple) and isinstance(constraint[1], int):
        return constraint[1]
    if isinstance(constraint, list) or isinstance(constraint, tuple):
        if constraint[0] in ["and", "or"]:
            val1 = constraintEval(infoDict, constraint[1], testcase, funcdic)
            if constraint[0] == "and" and not val1:
                return False
            if constraint[0] == "or" and val1:
                return True
            val2 = constraintEval(infoDict, constraint[2], testcase, funcdic)
            if constraint[0] == "and":
                return val1 and val2
            else:
                return val1 or val2
        if constraint[0] == "=>":
            val1 = constraintEval(infoDict, constraint[1], testcase, funcdic)
            if not val1:
                return True
            val2 = constraintEval(infoDict, constraint[2], testcase, funcdic)
            return val2
        if constraint[0] in ["=", "<=", "<", ">", ">=", "+", "-", "*"]:
            val1 = constraintEval(infoDict, constraint[1], testcase, funcdic)
            val2 = constraintEval(infoDict, constraint[2], testcase, funcdic)
            ope = constraint[0]
            if ope == "=":
                ope = "=="
            return eval(str(val1) + ope + str(val2))
        funcname = infoDict["funcname"]
        if constraint[0] == funcname:
            candval = funcdic[tuple(constraint[1:])]
            if isinstance(candval, int):
                return candval
            elif isinstance(candval, tuple):
                argdic = dict()
                for i, arg in enumerate(constraint[1:]):
                    argdic["arg" + str(i)] = arg
                infoDict["argd"] = argdic
                return constraintEval(infoDict, list(candval), testcase, funcdic)
            else:   # argx
                arg = int(candval[3:])
                assert(constraint[arg + 1] in testcase)
                return testcase[constraint[arg + 1]]
        else:
            print(constraint)
            exit("Error in consEval")
    assert(isinstance(constraint, str))
    if constraint not in testcase:
        constraint = infoDict["argd"][constraint]
    return testcase[constraint]

def checkoneAssign(infoDict, constraints, testcase, funcdic):
    for constraint in constraints:
        if not constraintEval(infoDict, constraint[1], testcase, funcdic):
            return False
    return True

def filterFunc(infoDict):
    def get(constraint, funcname):
        retlist = []
        if isinstance(constraint, list):
            if constraint[0] == funcname:
                return [tuple(constraint[1:])]
            for child in constraint:
                retlist += get(child, funcname)
        return retlist
    ret = []
    funcname = infoDict["funcname"]
    constraints = infoDict["cons"]
    for constraint in constraints:
        ret += get(constraint, funcname)
    return list(set(ret))

def partiTest(infoDict):
    constraints = infoDict["cons"]
    candidates = infoDict["cand"]
    testcases = infoDict["test"]
    fullset = set()
    funccalls = filterFunc(infoDict)
    for testcase in testcases:      # convert str arg to assigned value
        funclist = []
        for funccall in funccalls:
            assign = tuple(funccall)
            funclist.append(assign)
        tryretvalue = []
        assigndic = {}
        def dfs(funclist, assigndic, tryretvalue, depth, maxdepth):
            if depth == maxdepth:
                tryretvalue.append(cp(assigndic))
                return
            for cand in candidates:
                assigndic[funclist[depth]] = cand
                dfs(funclist, assigndic, tryretvalue, depth + 1, maxdepth)
            return
        dfs(funclist, assigndic, tryretvalue, 0, len(funclist))
        for assign in tryretvalue:
            if checkoneAssign(infoDict, constraints, testcase, assign):
                break
        # print(tryretvalue)
        for item in assign.items():
            item = (tuple(testcase[x] for x in item[0]), item[1])
            fullset.add(item)
    # print(fullset)
    fullList = [[] for _ in range(len(candidates))]
    for pair in fullset:
        fullList[candidates.index(pair[1])].append(pair[0])
    return fullList


def Filter(condList, testset):
    retset = set()
    for test in testset:
        sat = True
        for cond in condList:
            op = cond[0]
            if op == "=":
                op = "=="
            # print(cond)
            # print(str(test[cond[1]]) + op + str(test[cond[2]]))
            sat = eval(str(test[cond[1]]) + op + str(test[cond[2]]))
            if not sat:
                break
        if sat:
            retset.add(test)
    return retset

def search(infoDict, depth, fullList):
    
    # print(depth)
    # if depth > 0:
    #     print(infoDict["cond"][depth - 1])
    if depth == infoDict["maxdepth"]:
        return
    curset = set(fullList[depth])
    appendset = set([item for sublist in fullList[depth + 1:] for item in sublist])
    # print(curList)
    # print(fullList)
    opList = ["<=", "=", "<"]
    arglen = infoDict["argl"]
    condList = infoDict["cond"][depth]
    if len(appendset) == 0:
        return
    for i in range(arglen):
        for j in range(arglen):
            if i == j:
                continue
            for op in opList:
                condList.append([op, i, j])
                newapset = Filter(condList, appendset)
                newcurset = Filter(condList, curset)
                origl1 = len(curset)
                origl2 = len(appendset)
                newl1 = len(newcurset)
                newl2 = len(newapset)
                if origl1 != newl1 or origl2 == newl2:
                    condList.pop(-1)
                elif newl2 == 0:
                    search(infoDict, depth + 1, fullList)
                    return
                else:
                    appendset = newapset
    assert(False)   # should not execute here
    return

def candi2arg(candidate, args):
    if isinstance(candidate, tuple) or isinstance(candidate, list):
        return [candi2arg(v, args) for v in candidate]
    if isinstance(candidate, int):
        return str(candidate)
    if candidate[:3] == "arg":
        return args[int(candidate[3:])]
    return candidate

def buildCondition(conditions, args):
    if len(conditions) == 1:
        return [conditions[0][0], args[conditions[0][1]] \
                              , args[conditions[0][2]]]
    ret = ["and"] + [buildCondition(conditions[0:1], args)] \
                  + [buildCondition(conditions[1:], args)]
    return ret

def convert2Sygus(infoDict):
    funcdefine = ["define-fun"] + infoDict["synth"][1:4]
    funcdefineStr = translator.toString(funcdefine, ForceBracket=True)
    args = tuple(v[0] for v in infoDict["synth"][2])
    candidates = infoDict["cand"]
    conditions = infoDict["cond"]
    assert(len(candidates) - 1 == len(conditions))
    def dfs(candidates, args, conditions, depth):
        if depth == len(candidates) - 1:
            return candi2arg(candidates[-1], args)
        curconditions = conditions[depth]
        assert(len(curconditions) > 0)
        conditionStr = buildCondition(curconditions, args)
        return ["ite"] + [conditionStr] \
            + [candi2arg(candidates[depth], args)] \
            + [dfs(candidates, args, conditions, depth + 1)]
    curStr = dfs(candidates, args, conditions, depth=0)
    curStr = translator.toString(curStr)
    return funcdefineStr[:-1] + " " + curStr + funcdefineStr[-1]


def Solver(bmExpr):
    candidates = getCandidates(bmExpr)
    candidates = list(set(candidates))
    # print(candidates)
    dic = {}
    for i, candi in enumerate(candidates):
        dic[candi] = i
    constraints = getConstraints(bmExpr)
    varlist = getVarlist(bmExpr)
    maxdepth = len(candidates) - 1
    boolExp = [[] for _ in range(maxdepth)]
    depth = 0

    synth = getSynth(bmExpr)
    funcname = synth[1]
    testcases = generateTestcase(varlist, withmax="Idx" not in funcname)
    infoDict = {}
    infoDict["cand"] = candidates
    infoDict["cond"] = boolExp
    infoDict["maxdepth"] = maxdepth
    infoDict["cons"] = constraints
    infoDict["test"] = testcases
    infoDict["argl"] = len(synth[2])
    infoDict["funcname"] = funcname
    infoDict["synth"] = synth
    # print(testcases)
    fullList = partiTest(infoDict)
    # print(fullList)
    search(infoDict, depth, fullList)
    Ans = convert2Sygus(infoDict)
    return Ans