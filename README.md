### 程序综合-SyGus求解器

该项目实现了一个简单的SyGus求解器，解决了33个测试样例中的32个。该SyGus求解器自动生成测试输入、搜索可能满足条件的程序输出，再基于产生的输入输出对在程序空间中搜索满足条件的程序；我们称之为**数据驱动的SyGus求解器**。

#### SyGus

程序综合问题为给定程序空间（由程序语法确定），寻找满足特定约束的程序。

SyGus(Syntax-Guided Synthesis)是程序综合问题的标准化，输入输出格式由Synth-Lib定义，见[Language of SyGus](https://sygus.org/assets/pdf/SyGuS-IF.pdf).例如，$max_2$函数的语法和约束定义如下：

```
(synth-fun max2 ((x Int) (y Int)) Int
    ((Start Int (x
                 y
                 0
                 1
                 (+ Start Start)
                 (- Start Start)
                 (ite StartBool Start Start)))
    (StartBool Bool ((and StartBool StartBool)
                     (or StartBool StartBool)
                     (not StartBool)
                     (<= Start Start)
                     (= Start Start)
                     (>= Start Start)))))
```

```
(declare-var x Int)
(declare-var y Int)
(constraint (>= (max2 x y) x))
(constraint (>= (max2 x y) y))
(constraint (or (= x (max2 x y))
				(= y (max2 x y))))
(check-synth)
```

而一个满足要求的程序为：

```
(define-fun max2 ((x Int) (y Int)) Int (ite (<= y x) x y))
```

#### 基于宽度优先搜索的程序综合

我们在已有的SyGus Parser和宽度优先搜索程序上修复了一些bug，实现了普通的基于宽度优先搜索的程序综合。

程序空间中的每个程序都有对应的语法分析树，我们对语法分析树的最左派生过程进行宽度优先搜索。该算法可以保证在有限时间内给出问题的最简单解（派生步数最短的解）。但在实际运行中，由于搜索空间的指数增长，该算法通常只能求出简单程序的解。在实际测试中求出的解的派生步数一般不超过7.

#### 数据驱动的SyGus求解器

**问题观察**

$max$和$array\_search$问题中的目标程序都形如：

```
(ite BoolExp1 target1 (ite BoolExp2 target2 (... (ite BoolExpn targetn1 targetn2))))
```

搜索这类程序的困难之处在于搜索空间随表达式长度指数增长，而实际上搜索过程中的大部分程序都可以被中途剪枝。比如对于函数的输入输出对$(x,y)$，若：

$$Assign(BoolExp1,x)=True \and Assign(target1,x)\ne y$$

则后续的搜索不用继续下去。

通过这种剪枝方法，我们把原来随target个数指数增长的搜索空间减为线性增长。

**搜索算法**

我们的搜索算法过程如下：

```
1. 从约束定义中过滤候选目标targets
2. 枚举约束定义文件中定义变量的k种不同赋值
3. 递归搜索满足所有约束的函数返回值
4. 用2,3中生成的函数输入和返回值对搜索BoolExp
5. 用SMT Solver检测得到的程序prog是否满足要求，若满足，返回prog
6. k = k * 2; goto 2;
```

以$max2$为例说明算法的步骤：

$max2$的约束定义如下，

```
(declare-var x Int)
(declare-var y Int)

(constraint (>= (max2 x y) x))
(constraint (>= (max2 x y) y))
(constraint (or (= x (max2 x y))
				(= y (max2 x y))))
(check-synth)
```

步骤1：利用预先定义的规则过滤出函数可能的返回值为$[arg0, arg1]$。则我们最终产生的程序形如(ite BoolExp0 arg0 arg1)，其中BoolExp0待搜索。

步骤2：枚举变量$[x,y]$的不同赋值，例如$k=3$时一种可能的结果为$[(1,2),(2,1),(2,2)]$。

步骤3：我们枚举$[max2(1,2),max2(2,1),max2(2,2)]$的不同结果，然后代入constraint检查是否满足，最终得到满足条件的结果是以下两种：

$[max2(1,2)=arg1=2,max2(2,1)=arg0=2,max2(2,2)=arg0=2]$

$[max2(1,2)=arg1=2,max2(2,1)=arg0=2,max2(2,2)=arg1=2]$

经过前三步，我们得到两种可能的输入输出对：

$S_1=[(1,2)\rightarrow arg1,(2,1)\rightarrow arg0,(2,2)\rightarrow arg0]$

$S_2=[(1,2)\rightarrow arg1,(2,1)\rightarrow arg0,(2,2)\rightarrow arg1]$

步骤4：针对这两种可能的情况，我们分别进行BoolExp的搜索，步骤四的算法如下：

```
条件: S, 目标: BoolExps
设: BoolExpk = And(exp1, exp2, ..., expkn)
算法步骤：
1. 将输入输出对S按返回值分为n个集合，Si = {pair | pair.target == targeti}
2. for i = 1 to n:
		ni = 0
		S1 = Si
		S2 = Union(Sk), k > i
		remainSize = |S2|
		while remainSize > 0:
			从BoolExp空间中产生一条表达式exp
			exp_ni = exp
			Si1 = { pair | pair[0]满足exp and pair in S1}			
			Si2 = { pair | pair[0]满足exp and pair in S2}
			if |Si1| < |S1|:
				continue
			if |Si2| == 0:
				ni = ni + 1
            	break
			if |Si2| < |S2|:
				ni = ni + 1
				S2 = Si2
```

对于$S1$和$S2$步骤4分别求出一个满足输入输出对的目标程序，然后在步骤5中用SMT Solver确认生成的程序是否正确。若通过检测则搜索结束，否则在步骤6中增加枚举的赋值个数，生成更多的输入输出对，从步骤2开始重新搜索。

**算法分析**
该算法的局限性主要在于只对嵌套$ite$的目标程序搜索有优化，对于不满足这种情况的程序我们使用普通的宽度有限搜索。

在目标程序可被嵌套$ite$表达时，我们还假设$target_i$都能从$constraint$中抽取。在这两个条件满足的情况下，该算法的正确性是得到保证的。因为随着赋值枚举数量$k$的趋于无穷，朴素的枚举算法可以得到所有的输入情况，在整个输入空间上都满足约束的程序最终一定可以通过SMT Solver的检查。

**实际实现**

实际上，我们只实现了上述算法的一部分，与上述算法的区别在于：在第3步我们只搜索了一组满足条件的函数赋值，没有搜索所有情况；我们定义了一些启发式规则生成输入赋值，没有做迭代增加地赋值。即便如此，我们实现的Solver也通过了全部33个测试样例中的32个。