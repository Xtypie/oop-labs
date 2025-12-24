from math import pi, isclose
from typing import Self


class Angle:
    @classmethod
    def from_degree(cls, deg_value: float) -> Self:
        return cls(deg_value * (pi / 180))

    def __init__(self, rad_value: float) -> None:
        self._value = rad_value

    def __float__(self) -> float:
        return float(self._value)

    def __int__(self) -> int:
        return int(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"Angle({self._value})"

    @property
    def degree(self) -> float:
        return self._value * (180 / pi)

    @property
    def radian(self) -> float:
        return self._value

    @radian.setter
    def radian(self, val: float) -> None:
        self._value = val

    @degree.setter
    def degree(self, val: float) -> None:
        self._value = val * (pi / 180)

    def __eq__(self, other: Self) -> bool:
        return isclose(self._value % (2 * pi), other._value % (2 * pi), abs_tol=1e-9)

    def __ne__(self, other: Self) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Self) -> bool:
        return self._value % (2 * pi) < other._value % (2 * pi)

    def __le__(self, other: Self) -> bool:
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other: Self) -> bool:
        return self._value % (2 * pi) > other._value % (2 * pi)

    def __ge__(self, other: Self) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __add__(self, other: Self | int | float) -> Self:
        if isinstance(other, Angle):
            return Angle(self._value + other._value)
        elif isinstance(other, (int, float)):
            return Angle(self._value + other)
        else:
            return NotImplemented

    def __radd__(self, other: int | float) -> Self:
        return self.__add__(other)

    def __sub__(self, other: Self | int | float) -> Self:
        if isinstance(other, Angle):
            return Angle(self._value - other._value)
        elif isinstance(other, (int, float)):
            return Angle(self._value - other)
        else:
            return NotImplemented

    def __rsub__(self, other: int | float) -> Self:
        if isinstance(other, (int, float)):
            return Angle(other - self._value)
        return NotImplemented

    def __mul__(self, multiplier: int | float) -> Self:
        return Angle(self._value * multiplier)

    def __rmul__(self, multiplier: int | float) -> Self:
        return self.__mul__(multiplier)

    def __truediv__(self, denominator: int | float) -> Self:
        return Angle(self._value / denominator)



class AngleRange:
    def __init__(self, first: float | int, second: float | int,
                 first_incl: bool = True, second_incl: bool = True) -> None:
        self._first = first
        self._second = second
        self._first_incl = first_incl
        self._second_incl = second_incl

    @classmethod
    def from_angle(cls, ang: Angle) -> Self:
        return cls(0, ang.radian)

    @property
    def start(self) -> float | int:
        return self._first

    @property
    def end(self) -> float | int:
        return self._second

    @property
    def include_start(self) -> bool:
        return self._first_incl

    @property
    def include_end(self) -> bool:
        return self._second_incl

    def __abs__(self):
        if self._first <= self._second:
            return self._second - self._first
        else:
            return (2 * pi - self._first) + self._second

    def __repr__(self):
        left = "[" if self._first_incl else "("
        right = "]" if self._second_incl else ")"
        return f"AngleRange({left}{self._first}, {self._second}{right})"

    def __eq__(self, other: Self) -> bool:
        return (self.__abs__() == other.__abs__() and
                Angle(self._second) == Angle(other._second) and
                Angle(self._first) == Angle(other._first))

    def __ne__(self, other: Self) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Self) -> bool:
        return self.__abs__() < other.__abs__()

    def __le__(self, other: Self) -> bool:
        return self.__abs__() <= other.__abs__()

    def __gt__(self, other: Self) -> bool:
        return self.__abs__() > other.__abs__()

    def __ge__(self, other: Self) -> bool:
        return self.__abs__() >= other.__abs__()

    def __contains__(self, elem: Self | Angle) -> bool:
        if isinstance(elem, AngleRange):
            if abs(elem) > abs(self):
                return False

            f1, s1 = self._first, self._second
            f2, s2 = elem._first, elem._second

            def less_eq(x: float | int, y: float | int, inc: bool) -> bool:
                return x < y or (inc and x == y)

            def greater_eq(x: float | int, y: float | int, inc: bool) -> bool:
                return x > y or (inc and x == y)

            if f1 <= s1:
                if f2 <= s2:
                    ok_start = greater_eq(f2, f1, self._first_incl and elem._first_incl)
                    ok_end = less_eq(s2, s1, self._second_incl and elem._second_incl)
                    return ok_start and ok_end
                else:
                    len1 = s1 - f1
                    len2 = f2 + s2
                    if len1 == len2 and len1 % (2 * pi) == 0:
                        if (self._first_incl and self._second_incl and
                                elem._second_incl and elem._first_incl):
                            return True
                    return False
            else:
                if f2 <= s2:
                    in_first = greater_eq(f2, f1, self._first_incl and elem._first_incl)
                    in_second = less_eq(s2, s1, self._second_incl and elem._second_incl)
                    return in_first or in_second
                else:
                    in_first = greater_eq(f2, f1, self._first_incl and elem._first_incl)
                    in_second = less_eq(s2, s1, self._second_incl and elem._second_incl)
                    return in_first and in_second

        elif isinstance(elem, Angle):
            return self.__contains__(AngleRange.from_angle(elem))
        else:
            raise NotImplementedError

    def __add__(self, other: Self) -> list[Self]:
        a1, b1 = self._first % (2 * pi), self._second % (2 * pi)
        a2, b2 = other._first % (2 * pi), other._second % (2 * pi)

        segs1 = [(a1, b1, self._first_incl, self._second_incl)] if a1 <= b1 else [
            (a1, 2 * pi, self._first_incl, True),
            (0, b1, True, self._second_incl)
        ]
        segs2 = [(a2, b2, other._first_incl, other._second_incl)] if a2 <= b2 else [
            (a2, 2 * pi, other._first_incl, True),
            (0, b2, True, other._second_incl)
        ]

        all_segs = segs1 + segs2
        all_segs.sort(key=lambda t: t[0])

        res_segs = []
        cur_a, cur_b, cur_a_inc, cur_b_inc = all_segs[0]

        for x, y, x_inc, y_inc in all_segs[1:]:
            if x < cur_b or (x == cur_b and (cur_b_inc or x_inc)):
                if y > cur_b or (y == cur_b and y_inc):
                    cur_b = y
                    cur_b_inc = y_inc
            else:
                res_segs.append(AngleRange(cur_a, cur_b, cur_a_inc, cur_b_inc))
                cur_a, cur_b, cur_a_inc, cur_b_inc = x, y, x_inc, y_inc

        res_segs.append(AngleRange(cur_a, cur_b, cur_a_inc, cur_b_inc))
        return res_segs

    def __sub__(self, other: Self) -> list[Self]:
        a1, b1 = self._first % (2 * pi), self._second % (2 * pi)
        a2, b2 = other._first % (2 * pi), other._second % (2 * pi)

        segs1 = [(a1, b1, self._first_incl, self._second_incl)] if a1 <= b1 else [
            (a1, 2 * pi, self._first_incl, True),
            (0, b1, True, self._second_incl)
        ]
        segs2 = [(a2, b2, other._first_incl, other._second_incl)] if a2 <= b2 else [
            (a2, 2 * pi, other._first_incl, True),
            (0, b2, True, other._second_incl)
        ]

        final = []

        for s1, e1, s1_inc, e1_inc in segs1:
            temp = [(s1, e1, s1_inc, e1_inc)]
            for s2, e2, s2_inc, e2_inc in segs2:
                new_temp = []
                for ts, te, ts_inc, te_inc in temp:
                    if (te < s2 or (te == s2 and not (te_inc and s2_inc)) or
                            ts > e2 or (ts == e2 and not (ts_inc and e2_inc))):
                        new_temp.append((ts, te, ts_inc, te_inc))
                    else:
                        if ts < s2 or (ts == s2 and ts_inc and not s2_inc):
                            new_temp.append((ts, s2, ts_inc, not s2_inc))
                        if te > e2 or (te == e2 and te_inc and not e2_inc):
                            new_temp.append((e2, te, not e2_inc, te_inc))
                temp = new_temp
            final.extend([AngleRange(x, y, xi, yi) for x, y, xi, yi in temp])

        return final


print("Создание углов")
v1 = Angle(pi / 2)
v2 = Angle.from_degree(90)
print(v1, v2)

print("\nПолучение и присваивание")
print(v1.radian)
print(v1.degree)
v1.radian = pi
print(v1.radian, v1.degree)
v1.degree = 45
print(v1.radian, v1.degree)

print("\nПреобразования")
x = Angle(pi / 2)
print(float(x), int(x), str(x), repr(x))

print("\nСравнение углов")
x = Angle(0)
y = Angle(2 * pi)
z = Angle(pi)
print(x == y)
print(x != z)
print(x < z)
print(z > y)
print(x <= y)
print(z >= y)

print("\nАрифметика")
x = Angle(pi / 2)
y = Angle(pi / 4)
print(x + y)
print(x - y)
print(x + pi / 4)
print(pi / 4 + x)
print(x - pi / 4)
print(pi / 2 - x)
print(x * 2)
print(2 * x)
print(x / 2)

print("\nСоздание диапазонов")
rg1 = AngleRange(0, pi / 2)
rg2 = AngleRange(pi / 2, pi)
rg3 = AngleRange(3 * pi / 2, pi / 2)
rg4 = AngleRange(0, pi * 2)
print(rg1)
print(rg2)
print(rg3)

print("\nДлина диапазона")
print(abs(rg1))
print(abs(rg3))

print("\nПроверка вхождения углов в диапазон")
p = Angle(pi / 4)
q = Angle(3 * pi / 2)
print(p in rg1)
print(q in rg4)
print(q in rg3)

print("\nПроверка вхождения диапазонов")
r4 = AngleRange(0, pi)
r5 = AngleRange(pi / 4, pi / 2)
r6 = AngleRange(pi / 2, 3 * pi / 2)
print(r5 in r4)
print(r6 in r4)
print(rg3 in r4)
print(r4 in rg3)

print("\nПроверка включающих и исключающих границ")
r7 = AngleRange(0, pi, first_incl=False, second_incl=False)
print(Angle(0) in r7)
print(Angle(pi) in r7)
print(AngleRange(pi / 4, pi / 2) in r7)

print("\nСравнение диапазоно")
r8 = AngleRange(0, pi)
r9 = AngleRange(pi, 2 * pi)
r10 = AngleRange(0, 2 * pi)
print(r8 < r9)
print(r8 == r9)
print(r10 > r8)

def fmt_range(rg):
    a = rg.start
    b = rg.end
    left = "[" if rg.include_start else "("
    right = "]" if rg.include_end else ")"
    return f"{left}{a:.1f}, {b:.1f}{right}"


def fmt_deg(rg):
    a_deg = rg.start * 180 / pi
    b_deg = rg.end * 180 / pi
    left = "[" if rg.include_start else "("
    right = "]" if rg.include_end else ")"
    return f"{left}{a_deg:.0f}°, {b_deg:.0f}°{right}"


print("\nCложение:")
rg1 = AngleRange(120 * pi / 180, 200 * pi / 180)
rg2 = AngleRange(150 * pi / 180, 240 * pi / 180)
res = rg1 + rg2
print(f"{fmt_deg(rg1)} + {fmt_deg(rg2)} = {[fmt_deg(r) for r in res]}")

print("\nВычитание из середины:")
rg5 = AngleRange(0, pi)
rg6 = AngleRange(pi / 4, 3 * pi / 4)
res = rg5 - rg6
print(f"{fmt_deg(rg5)} - {fmt_deg(rg6)} = {[fmt_deg(r) for r in res]}")

print("\nВычитание wrap-around диапазона:")
rg7 = AngleRange(270 * pi / 180, 90 * pi / 180)
rg8 = AngleRange(300 * pi / 180, 30 * pi / 180)
res = rg7 - rg8
print(f"{fmt_deg(rg7)} - {fmt_deg(rg8)} = {[fmt_deg(r) for r in res]}")

print("\nСложное вычитание с границами:")
rg9 = AngleRange(pi / 6, 5 * pi / 6)
rg10 = AngleRange(pi / 3, 2 * pi / 3)
res = rg9 - rg10
print(f"{fmt_deg(rg9)} - {fmt_deg(rg10)} = {[fmt_deg(r) for r in res]}")

print("\nСложение непересекающихся диапазонов:")
rg11 = AngleRange(0, pi / 4)
rg12 = AngleRange(pi / 2, 3 * pi / 4)
res = rg11 + rg12
print(f"{fmt_deg(rg11)} + {fmt_deg(rg12)} = {[fmt_deg(r) for r in res]}")

print("\nВычитание всего диапазона:")
rg13 = AngleRange(pi / 4, 3 * pi / 4)
rg14 = AngleRange(pi / 4, 3 * pi / 4)
res = rg13 - rg14
print(f"{fmt_deg(rg13)} - {fmt_deg(rg14)} = {[fmt_deg(r) for r in res]}")

print("\nСложение с исключающими границами:")
rg15 = AngleRange(0, pi / 2, second_incl=False)
rg16 = AngleRange(pi / 2, pi, first_incl=False)
res = rg15 + rg16
print(f"{fmt_deg(rg15)} + {fmt_deg(rg16)} = {[fmt_deg(r) for r in res]}")

print("\nВычитание с граничными условиями:")
rg17 = AngleRange(0, pi)
rg18 = AngleRange(pi / 2, pi / 2)
res = rg17 - rg18
print(f"{fmt_deg(rg17)} - {fmt_deg(rg18)} = {[fmt_deg(r) for r in res]}")