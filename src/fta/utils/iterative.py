def iterate(cache, root, dependencies, combine):
    if root in cache:
        return cache[root]
    stack = [root]
    while stack:
        key = stack[-1]
        if key in cache:
            stack.pop()
            continue
        missing = [dep for dep in dependencies(key) if dep not in cache]
        if missing:
            stack.extend(missing)
        else:
            stack.pop()
            cache[key] = combine(key)
    return cache[root]