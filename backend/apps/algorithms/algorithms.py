"""Implementaciones explícitas usadas por la demostración académica.

No reemplazan los índices ni el ordenamiento de la base de datos en los flujos
transaccionales. Se aplican sobre instantáneas pequeñas de datos de negocio para
que su comportamiento, complejidad y resultado puedan revisarse en clase.
"""
from math import ceil


def bubble_sort(items, key):
    """Bubble Sort estable, O(n²), sin modificar la colección de entrada."""
    result = list(items)
    for end in range(len(result) - 1, 0, -1):
        swapped = False
        for index in range(end):
            if key(result[index]) > key(result[index + 1]):
                result[index], result[index + 1] = result[index + 1], result[index]
                swapped = True
        if not swapped:
            break
    return result


def insertion_sort(items, key):
    """Insertion Sort estable, O(n²), práctico sobre listas pequeñas."""
    result = list(items)
    for index in range(1, len(result)):
        current = result[index]
        position = index - 1
        while position >= 0 and key(result[position]) > key(current):
            result[position + 1] = result[position]
            position -= 1
        result[position + 1] = current
    return result


def quick_sort(items, key):
    """Quick Sort funcional, O(n log n) promedio y O(n²) en peor caso."""
    values = list(items)
    if len(values) <= 1:
        return values
    pivot = key(values[len(values) // 2])
    lower = [item for item in values if key(item) < pivot]
    equal = [item for item in values if key(item) == pivot]
    higher = [item for item in values if key(item) > pivot]
    return quick_sort(lower, key) + equal + quick_sort(higher, key)


def binary_search(items, target, key):
    """Busca un valor exacto en una colección ya ordenada: O(log n)."""
    low, high = 0, len(items) - 1
    while low <= high:
        middle = (low + high) // 2
        value = key(items[middle])
        if value == target:
            return middle
        if value < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1


def greedy_change(amount, denominations):
    """Selecciona primero la mayor denominación que cabe en el cambio."""
    if amount < 0:
        raise ValueError("The change amount cannot be negative.")
    remaining, result = amount, []
    for denomination in sorted(set(denominations), reverse=True):
        count, remaining = divmod(remaining, denomination)
        if count:
            result.append({"denomination": denomination, "count": count})
    return result, remaining


def lexicographically_greatest(value):
    """Construye de forma voraz la mayor cadena posible por extremos."""
    result = ""
    for character in value:
        result = character + result if not result or character >= result[0] else result + character
    return result


def knapsack_01(items, capacity):
    """Mochila 0/1 por programación dinámica.

    Cada elemento se selecciona como máximo una vez. Los pesos y la capacidad
    son unidades enteras para mantener el tamaño de la tabla acotado.
    """
    if capacity < 0:
        raise ValueError("Capacity cannot be negative.")
    table = [[0] * (capacity + 1) for _ in range(len(items) + 1)]
    for item_index, item in enumerate(items, start=1):
        weight, benefit = item["weight"], item["benefit"]
        for current_capacity in range(capacity + 1):
            table[item_index][current_capacity] = table[item_index - 1][current_capacity]
            if weight <= current_capacity:
                table[item_index][current_capacity] = max(
                    table[item_index][current_capacity],
                    table[item_index - 1][current_capacity - weight] + benefit,
                )

    selected, remaining = [], capacity
    for item_index in range(len(items), 0, -1):
        if table[item_index][remaining] != table[item_index - 1][remaining]:
            item = items[item_index - 1]
            selected.append(item)
            remaining -= item["weight"]
    selected.reverse()
    return selected, table[-1][-1]


def inventory_knapsack(products, budget):
    """Recomienda una unidad de productos con mayor margen bajo un presupuesto.

    Se usan bloques de COP 1,000 como peso; redondear el costo hacia arriba
    garantiza que la recomendación nunca exceda el presupuesto real.
    """
    unit = 1000
    candidates = [
        {
            **product,
            "weight": ceil(product["purchase_price"] / unit),
            "benefit": max(product["sale_price"] - product["purchase_price"], 0),
        }
        for product in products
        if product["purchase_price"] > 0
    ]
    selected, benefit = knapsack_01(candidates, budget // unit)
    return selected, benefit
