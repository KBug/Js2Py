from operations import *

class OP_CODE(object):
    _params = []
    # def eval(self, ctx):
    #     raise

    def __repr__(self):
        return self.__class__.__name__ + str(tuple([getattr(self, e) for e in self._params]))


# --------------------- UNARY ----------------------

class UNARY_OP(OP_CODE):
    _params = ['operator']
    def __init__(self, operator):
        self.operator = operator

    def eval(self, ctx):
        val = ctx.stack.pop()
        ctx.stack.append(UNARY_OPERATIONS[self.operator](val))


# special unary operations

class TYPEOF(OP_CODE):
    _params = ['identifier']
    def __init__(self, identifier):
        self.identifier = identifier

    def eval(self, ctx):
        # typeof something_undefined  does not throw reference error
        val = ctx.get(self.identifier, False) # <= this makes it slightly different!
        ctx.stack.append(typeof_uop(val))



class POSTFIX(OP_CODE):
    _params = ['identifier', 'post', 'incr']
    def __init__(self, identifier, post, incr):
        self.identifier = identifier
        self.change_before = 1 if incr else -1
        self.change_after = -self.change_before if post else 0

    def eval(self, ctx):
        target = to_number(ctx.get(self.identifier)) + self.change_before
        ctx.put(self.identifier, target)
        ctx.stack.append(target + self.change_after)


class POSTFIX_MEMBER(OP_CODE):
    _params = ['post', 'incr']

    def __init__(self, post, incr):
        self.change_before = 1 if incr else -1
        self.change_after = -self.change_before if post else 0

    def eval(self, ctx):
        name = ctx.stack.pop()
        left = ctx.stack.pop()

        target = to_number(get_member(left, name, ctx.space)) + self.change_before
        if type(left) not in PRIMITIVES:
            left.put_member(name, target)

        ctx.stack.append(target + self.change_after)

class POSTFIX_MEMBER_DOT(OP_CODE):
    _params = ['post', 'incr', 'prop']

    def __init__(self, post, incr, prop):
        self.change_before = 1 if incr else -1
        self.change_after = -self.change_before if post else 0
        self.prop = prop

    def eval(self, ctx):
        left = ctx.stack.pop()

        target = to_number(get_member_dot(left, self.prop, ctx.space)) + self.change_before
        if type(left) not in PRIMITIVES:
            left.put(self.prop, target)

        ctx.stack.append(target + self.change_after)


class DELETE(OP_CODE):
    _params = ['name']

    def __init__(self, name):
        self.name = name

    def eval(self, ctx):
        ctx.stack.append(ctx.delete(self.name))


class DELETE_MEMBER(OP_CODE):
    def eval(self, ctx):
        prop = to_string(ctx.stack.pop())
        obj = to_object(ctx.stack.pop(), ctx)
        ctx.stack.append(obj.delete(prop, False))


# --------------------- BITWISE ----------------------

class BINARY_OP(OP_CODE):
    _params = ['operator']
    def __init__(self, operator):
        self.operator = operator

    def eval(self, ctx):
        right = ctx.stack.pop()
        left = ctx.stack.pop()
        ctx.stack.append(BINARY_OPERATIONS[self.operator](left, right))

# &&, || and conditional are implemented in bytecode


# --------------------- JUMPS ----------------------

# simple label that will be removed from code after compilation. labels ID will be translated
# to source code position.
class LABEL(OP_CODE):
    _params = ['num']
    def __init__(self, num):
        self.num = num


# I implemented interpreter in the way that when an integer is returned by eval operation the execution will jump
# to the location of the label (it is loc = label_locations[label])

class BASE_JUMP(OP_CODE):
    _params = ['label']
    def __init__(self, label):
        self.label = label

class JUMP(BASE_JUMP):
    def eval(self, ctx):
        return self.label

class JUMP_IF_TRUE(BASE_JUMP):
    def eval(self, ctx):
        val = ctx.stack.pop()
        if to_boolean(val):
            return self.label

class JUMP_IF_TRUE_WITHOUT_POP(BASE_JUMP):
    def eval(self, ctx):
        val = ctx.stack[-1]
        if to_boolean(val):
            return self.label

class JUMP_IF_FALSE(BASE_JUMP):
    def eval(self, ctx):
        val = ctx.stack.pop()
        if not to_boolean(val):
            return self.label

class JUMP_IF_FALSE_WITHOUT_POP(BASE_JUMP):
    def eval(self, ctx):
        val = ctx.stack[-1]
        if not to_boolean(val):
            return self.label

class POP(OP_CODE):
    def eval(self, ctx):
        del ctx.stack[-1]

class REDUCE(OP_CODE):
    def eval(self, ctx):
        assert len(ctx.stack)==2
        ctx.stack[0] = ctx.stack[1]
        del ctx.stack[1]


# --------------- LOADING --------------


class LOAD_NONE(OP_CODE):  # be careful with this :)
    def eval(self, ctx):
        ctx.stack.append(None)


class LOAD_N_TUPLE(OP_CODE): # loads the tuple composed of n last elements on stack. elements are popped.
    _params = ['n']
    def __init__(self, n):
        self.n = n

    def eval(self, ctx):
        tup = tuple(ctx.stack[-self.n:])
        del ctx.stack[-self.n:]
        ctx.stack.append(tup)


class LOAD_UNDEFINED(OP_CODE):
    def eval(self, ctx):
        ctx.stack.append(undefined)


class LOAD_NULL(OP_CODE):
    def eval(self, ctx):
        ctx.stack.append(null)


class LOAD_BOOLEAN(OP_CODE):
    _params = ['val']
    def __init__(self, val):
        assert val in (0, 1)
        self.val = bool(val)

    def eval(self, ctx):
        ctx.stack.append(self.val)


class LOAD_STRING(OP_CODE):
    _params = ['val']
    def __init__(self, val):
        assert isinstance(val, basestring)
        self.val = unicode(val)

    def eval(self, ctx):
        ctx.stack.append(self.val)


class LOAD_NUMBER(OP_CODE):
    _params = ['val']
    def __init__(self, val):
        assert isinstance(val, (float, int, long))
        self.val = float(val)

    def eval(self, ctx):
        ctx.stack.append(self.val)


class LOAD_REGEXP(OP_CODE):
    _params = ['body', 'flags']
    def __init__(self, body, flags):
        self.body = body
        self.flags = flags

    def eval(self, ctx):
        # we have to generate a new regexp - they are mutable
        ctx.stack.append(ctx.space.NewRegExp(self.body, self.flags))


class LOAD_FUNCTION(OP_CODE):
    pass


class LOAD_OBJECT(OP_CODE):
    _params = ['props']  # props are py string pairs (prop_name, kind): kind can be either i, g or s. (init, get, set)
    def __init__(self, props):
        self.num = len(props)
        self.props = props

    def eval(self, ctx):
        obj = ctx.space.NewObject()
        obj._init(self.props, ctx.stack[-self.num:], ctx.strict)
        del ctx.stack[-self.num:]
        ctx.stack.append(obj)


class LOAD_ARRAY(OP_CODE):
    _params = ['num']
    def __init__(self, num):
        self.num = num

    def eval(self, ctx):
        arr = ctx.space.NewArray(self.num)
        arr._init(ctx.stack[-self.num:])
        del ctx.stack[-self.num:]
        ctx.stack.append(arr)


class LOAD_THIS(OP_CODE):
    def eval(self, ctx):
        ctx.stack_append(ctx.THIS_BINDING)


class LOAD(OP_CODE): # todo check!
    _params = ['identifier']

    def __init__(self, identifier):
        self.identifier = identifier

    # 11.1.2
    def eval(self, ctx):
        ctx.stack.append(ctx.get(self.identifier))


class LOAD_MEMBER(OP_CODE):
    def eval(self, ctx):
        prop = ctx.stack.pop()
        obj = ctx.stack.pop()
        ctx.stack.append(get_member(obj, prop, ctx.space))


class LOAD_MEMBER_DOT(OP_CODE):
    _params = ['prop']
    def __init__(self, prop):
        self.prop = prop

    def eval(self, ctx):
        obj = ctx.stack.pop()
        ctx.stack.append(get_member_dot(obj, self.prop, ctx.space))



# --------------- STORING --------------


class STORE(OP_CODE):
    _params = ['identifier']
    def __init__(self, identifier):
        self.identifier = identifier

    def eval(self, ctx):
        value = ctx.stack[-1]  # don't pop
        ctx.put(self.identifier, value)


class STORE_MEMBER(OP_CODE):
    def eval(self, ctx):
        value = ctx.stack.pop()
        name = ctx.stack.pop()
        left = ctx.stack.pop()

        typ = type(left)
        if typ in PRIMITIVES:
            prop = to_string(name)
            if typ == NULL_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of null" % prop)
            elif typ == UNDEFINED_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of undefined" % prop)
            # just ignore...
        else:
            left.put_member(name, value)

        ctx.stack.append(value)


class STORE_MEMBER_DOT(OP_CODE):
    _params = ['prop']
    def __init__(self, prop):
        self.prop = prop

    def eval(self, ctx):
        value = ctx.stack.pop()
        left = ctx.stack.pop()

        typ = type(left)
        if typ in PRIMITIVES:
            if typ == NULL_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of null" % self.prop)
            elif typ == UNDEFINED_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of undefined" % self.prop)
            # just ignore...
        else:
            left.put(self.prop, value)
        ctx.stack.append(value)


class STORE_OP(OP_CODE):
    _params = ['identifier', 'op']

    def __init__(self, identifier, op):
        self.identifier = identifier
        self.op = op

    def eval(self, ctx):
        value = ctx.stack.pop()
        new_value = BINARY_OPERATIONS[self.op](ctx.get(self.identifier), value)
        ctx.put(self.identifier, new_value)
        ctx.stack.append(new_value)


class STORE_MEMBER_OP(OP_CODE):
    _params = ['op']
    def __init__(self, op):
        self.op = op

    def eval(self, ctx):
        value = ctx.stack.pop()
        name = ctx.stack.pop()
        left = ctx.stack.pop()

        typ = type(left)
        if typ in PRIMITIVES:
            if typ is NULL_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of null" % to_string(name))
            elif typ is UNDEFINED_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of undefined" % to_string(name))
            ctx.stack.append(BINARY_OPERATIONS[self.op](value, get_member(left, name, ctx.space)))
            return
        else:
            ctx.stack.append(BINARY_OPERATIONS[self.op](value, get_member(left, name, ctx.space)))
            left.put_member(name, ctx.stack[-1])


class STORE_MEMBER_DOT_OP(OP_CODE):
    _params = ['prop', 'op']
    def __init__(self, prop, op):
        self.prop = prop
        self.op = op

    def eval(self, ctx):
        value = ctx.stack.pop()
        left = ctx.stack.pop()

        typ = type(left)
        if typ in PRIMITIVES:
            if typ == NULL_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of null" % self.prop)
            elif typ == UNDEFINED_TYPE:
                raise MakeError('TypeError', "Cannot set property '%s' of undefined" % self.prop)
            ctx.stack.append(BINARY_OPERATIONS[self.op](value, get_member_dot(left, self.prop, ctx.space)))
            return
        else:
            ctx.stack.append(BINARY_OPERATIONS[self.op](value, get_member_dot(left, self.prop, ctx.space)))
            left.put_member_dot(self.prop, ctx.stack[-1])


# --------------- CALLS --------------

def bytecode_call(ctx, func, this, args):
    if type(func) is not PyJsFunction:
        raise MakeError('TypeError', "%s is not a function" % Type(func) )
    if func.is_native: # call to built-in function or method
        ctx.stack.append(func.code(this, args))
        return None

    # therefore not native. we have to return (new_context, function_label) to instruct interpreter to call
    return func._generate_my_context(this, args), func.code


class CALL(OP_CODE):
    def eval(self, ctx):
        args = ctx.stack_pop()
        func = ctx.stack_pop()

        return bytecode_call(ctx, func, ctx.exe.GLOBAL_THIS, args)


class CALL_METHOD(OP_CODE):
    def eval(self, ctx):
        args = ctx.stack.pop()
        prop = ctx.stack.pop()
        base = ctx.stack.pop()

        func = get_member(base, prop, ctx.space)

        return bytecode_call(ctx, func, base, args)


class CALL_METHOD_DOT(OP_CODE):
    _params = ['prop']
    def __init__(self, prop):
        self.prop = prop

    def eval(self, ctx):
        args = ctx.stack.pop()
        base = ctx.stack.pop()

        func = get_member_dot(base, self.prop, ctx.space)

        return bytecode_call(ctx, func, base, args)


class CALL_NO_ARGS(OP_CODE):
    def eval(self, ctx):
        func = ctx.stack_pop()

        return bytecode_call(ctx, func, ctx.exe.GLOBAL_THIS, ())


class CALL_METHOD_NO_ARGS(OP_CODE):
    def eval(self, ctx):
        prop = ctx.stack.pop()
        base = ctx.stack.pop()

        func = get_member(base, prop, ctx.space)

        return bytecode_call(ctx, func, base, ())


class CALL_METHOD_DOT_NO_ARGS(OP_CODE):
    _params = ['prop']
    def __init__(self, prop):
        self.prop = prop

    def eval(self, ctx):
        base = ctx.stack.pop()

        func = get_member_dot(base, self.prop, ctx.space)

        return bytecode_call(ctx, func, base, ())



class RETURN(OP_CODE):
    def eval(self, ctx):  # remember to load the return value on stack before using RETURN op.
        return (None, None)


class NEW(OP_CODE):
    def eval(self, ctx):
        args = ctx.stack.pop()
        constructor = ctx.stack.pop()
        if type(constructor) in PRIMITIVES or not constructor.IS_CONTRUCTOR:
            raise MakeError('TypeError', '%s is not a constructor' % Type(constructor))
        ctx.stack.append(constructor.create(args))


class NEW_NO_ARGS(OP_CODE):
    def eval(self, ctx):
        constructor = ctx.stack_pop()
        if type(constructor) in PRIMITIVES or not constructor.IS_CONTRUCTOR:
            raise MakeError('TypeError', '%s is not a constructor' % Type(constructor))
        ctx.stack.append(constructor.create(()))


# --------------- EXCEPTIONS --------------


class THROW(OP_CODE):
    def eval(self, ctx):
        raise MakeError(None, None, ctx.stack.pop())


class TRY_CATCH_FINALLY(OP_CODE):
    _params = []
    def __init__(self):
        pass

    def eval(self, ctx):
        pass



# ------------ WITH + ITERATORS ----------



# all opcodes...
OP_CODES = {}
g = ''
for g in globals():
    try:
        if not issubclass(globals()[g], OP_CODE) or g is 'OP_CODE':
            continue
    except:
        continue
    OP_CODES[g] = globals()[g]
