import numpy as np
import random


class CustomMutation:
    """
    Кастомная random mutation для PyGAD с адаптивным размахом.

    Настройки передаются из main при создании экземпляра.
    Амплитуда мутации выбирается по максимальному fitness последнего поколения:
      - размах LOW при max_fitness < threshold (плохое поколение -> широкий поиск)
      - размах HIGH при max_fitness >= threshold (хорошее поколение -> тонкая настройка)
    """

    def __init__(self,
                 mutation_range_low_fitness=0.30,
                 mutation_range_high_fitness=0.05,
                 fitness_threshold=20):
        """
        :param mutation_range_low_fitness: размах мутации (доля диапазона гена)
                                           при низком max fitness.
        :param mutation_range_high_fitness: размах мутации (доля диапазона гена)
                                            при высоком max fitness.
        :param fitness_threshold: порог для переключения размаха.
        """
        self.mutation_range_low_fitness = mutation_range_low_fitness
        self.mutation_range_high_fitness = mutation_range_high_fitness
        self.fitness_threshold = fitness_threshold

    def __call__(self, offspring, ga_instance):
        """
        Метод-обёртка, чтобы экземпляр класса можно было передать
        в pygad как mutation_type.
        """
        return self.mutate(offspring, ga_instance)

    def mutate(self, offspring, ga_instance):
        # Параметры из экземпляра pygad
        mutation_probability = ga_instance.mutation_probability
        mutation_num_genes = ga_instance.mutation_num_genes
        gene_space = ga_instance.gene_space

        num_genes = offspring.shape[1]

        # --- Максимальный fitness последнего поколения ---
        max_fitness = self._get_last_generation_max_fitness(ga_instance)

        # --- Выбираем размах мутации по max fitness поколения ---
        if max_fitness is None or max_fitness < self.fitness_threshold:
            mutation_percent = self.mutation_range_low_fitness
        else:
            mutation_percent = self.mutation_range_high_fitness

        # --- Мутируем потомков ---
        for idx in range(offspring.shape[0]):
            gene_indices = self._select_genes_to_mutate(
                num_genes, mutation_probability, mutation_num_genes
            )

            for gene_idx in gene_indices:
                low, high = self._get_gene_bounds(gene_space, gene_idx)

                if low is None or high is None:
                    gene_range = abs(offspring[idx, gene_idx]) or 1.0
                else:
                    gene_range = high - low

                # Размах мутации в абсолютных единицах
                mutation_amplitude = gene_range * mutation_percent

                # Random mutation внутри размаха [-amplitude, +amplitude]
                mutation_value = random.uniform(-mutation_amplitude,
                                                mutation_amplitude)

                # mutation_by_replacement = False -> прибавляем к гену
                offspring[idx, gene_idx] += mutation_value

                # Ограничиваем границами gene_space
                if low is not None and high is not None:
                    offspring[idx, gene_idx] = np.clip(
                        offspring[idx, gene_idx], low, high
                    )

        return offspring

    # ---------- Вспомогательные методы ----------

    @staticmethod
    def _get_last_generation_max_fitness(ga_instance):
        """
        Возвращает максимальный fitness последнего рассчитанного поколения.
        Не пересчитывает fitness для отдельных особей.
        """
        # PyGAD хранит fitness текущего поколения в last_generation_fitness
        last_fitness = getattr(ga_instance, 'last_generation_fitness', None)
        if last_fitness is not None and len(last_fitness) > 0:
            return float(np.max(last_fitness))

        # Резервный вариант: история лучших решений
        best_solutions_fitness = getattr(ga_instance,
                                          'best_solutions_fitness', None)
        if best_solutions_fitness:
            return float(best_solutions_fitness[-1])

        # На первой генерации данных ещё нет
        return None

    @staticmethod
    def _select_genes_to_mutate(num_genes, mutation_probability,
                                mutation_num_genes):
        """
        Возвращает индексы генов для мутации.
        Приоритет у mutation_probability, иначе mutation_num_genes.
        """
        if mutation_probability is not None:
            return [i for i in range(num_genes)
                    if random.random() < mutation_probability]
        elif mutation_num_genes is not None:
            n = min(mutation_num_genes, num_genes)
            return random.sample(range(num_genes), n)
        else:
            return [random.randint(0, num_genes - 1)]

    @staticmethod
    def _get_gene_bounds(gene_space, gene_idx):
        """
        Извлекает (low, high) диапазон для конкретного гена из gene_space.
        Поддерживает разные форматы gene_space в pygad.
        """
        if gene_space is None:
            return None, None

        # Индивидуальный dict для каждого гена
        if isinstance(gene_space, (list, tuple)) and len(gene_space) > gene_idx \
                and isinstance(gene_space[gene_idx], dict):
            space = gene_space[gene_idx]
            return space.get('low'), space.get('high')

        # Один общий dict для всех генов
        if isinstance(gene_space, dict):
            return gene_space.get('low'), gene_space.get('high')

        # Список значений
        if isinstance(gene_space, (list, tuple, np.ndarray)):
            if len(gene_space) > gene_idx and \
                    isinstance(gene_space[gene_idx], (list, tuple, np.ndarray)):
                values = gene_space[gene_idx]
                return min(values), max(values)
            return min(gene_space), max(gene_space)

        return None, None
