
(set-logic LIA)

(synth-fun fsearchIdx ((x Int) (y Int) (z Int)) Int
    ((Start Int (x
                 y
                 z
                 0
                 1
                 2
                 3
                 10
                 (+ Start Start)
                 (- Start Start)
                 (* Start Start)
		 (* Start Start)
                 (ite StartBool Start Start)))
     (StartBool Bool ((and StartBool StartBool)
                      (or  StartBool StartBool)
                      (not StartBool)
                      (<=  Start Start)
                      (=   Start Start)
                      (>=  Start Start)))))

(declare-var x Int)
(declare-var y Int)
(declare-var z Int)

(constraint (=> (< x y) (=> (< z x) (= (fsearchIdx x y z) (* y (+ x z))))))
(constraint (=> (< x y) (=> (> z y) (= (fsearchIdx x y z) (+ z (+ y x))))))
(constraint (=> (< x y) (=> (and (> z x) (< z y)) (= (fsearchIdx x y z) (* x (+ z y))))))

(check-synth)

