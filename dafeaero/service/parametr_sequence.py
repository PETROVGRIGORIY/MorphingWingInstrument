from typing import Iterator


class ParameterSequence:
    """Универсальная последовательность чисел (целых или дробных),
    может хранить лишь одно значение.
    Примеры:
        ParameterSequence(15)          -> [15] (одно значение)
        ParameterSequence(0, 10)       -> [0, 1, 2, ..., 10] (шаг по умолчанию 1)
        ParameterSequence(0, 10, 2)    -> [0, 2, 4, 6, 8, 10]
        ParameterSequence(10, 0, -2)   -> [10, 8, 6, 4, 2, 0]
    """
    __slots__ = ('_start', '_stop', '_step')

    def __init__(
        self, 
        start: int | float, 
        stop: int | float | None = None, 
        step: int | float | None = None
    ):
        self._start = start
        
        if stop is None:
            # Если передано одно значение
            self._stop = start
            self._step = 1
        else:
            self._stop = stop
            # Если шаг не указан, автоматически определяем направление
            if step is None:
                self._step = 1 if start < stop else -1
            else:
                self._step = step
                
        # Валидация
        if self._step == 0:
            raise ValueError("Шаг (step) не может быть равен нулю")
        if self._start < self._stop and self._step < 0:
            raise ValueError("Если start < stop, шаг должен быть положительным")
        if self._start > self._stop and self._step > 0:
            raise ValueError("Если start > stop, шаг должен быть отрицательным")

    @property
    def start(self) -> int | float:
        return self._start

    @property
    def stop(self) -> int | float:
        return self._stop

    @property
    def step(self) -> int | float:
        return self._step

    def values(self) -> list[int | float]:
        """Генерирует список значений последовательности."""
        if self.start == self.stop:
            return [self.start]
            
        n_steps = int(abs((self.stop - self.start) / self.step) + 1e-9)
        return [round(self.start + i * self.step, 10) for i in range(n_steps + 1)]

    def __iter__(self) -> Iterator[int | float]:
        """Позволяет использовать объект прямо в цикле for."""
        yield from self.values()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParameterSequence):
            return NotImplemented
        return (self.start, self.stop, self.step) == (other.start, other.stop, other.step)

    def __hash__(self) -> int:
        return hash((self.start, self.stop, self.step))

    def __repr__(self) -> str:
        if self.start == self.stop:
            return f"ParameterSequence({self.start})"
        return f"ParameterSequence({self.start}, {self.stop}, {self.step})"
