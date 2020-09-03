# stdlib
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Union

# third party
from nacl.signing import VerifyKey
from google.protobuf.reflection import GeneratedProtocolMessageType

# syft relative
from ....common.uid import UID
from ....io.address import Address
from ....pointer.pointer import Pointer
from ...abstract.node import AbstractNode
from .common import ImmediateActionWithoutReply
from ....store.storeable_object import StorableObject
from ....common.serde.deserialize import _deserialize
from .....decorators.syft_decorator_impl import syft_decorator
from .....proto.core.node.common.action.run_function_or_constructor_pb2 import (
    RunFunctionOrConstructorAction as RunFunctionOrConstructorAction_PB,
)


class RunFunctionOrConstructorAction(ImmediateActionWithoutReply):
    def __init__(
        self,
        path: str,
        args: Tuple[Any, ...],
        kwargs: Dict[Any, Any],
        id_at_location: UID,
        address: Address,
        msg_id: Optional[UID] = None,
    ):
        super().__init__(address=address, msg_id=msg_id)
        self.path = path
        self.args = args
        self.kwargs = kwargs

        # TODO: eliminate this explicit parameter and just set the object
        #  id on the object directly
        self.id_at_location = id_at_location

    @staticmethod
    def intersect_keys(
        left: Union[Dict[VerifyKey, UID], None], right: Dict[VerifyKey, UID]
    ) -> Dict[VerifyKey, UID]:
        # FIXME duplicated in run_class_method_action.py
        # get the intersection of the dict keys, the value is the request_id
        # if the request_id is different for some reason we still want to keep it,
        # so only intersect the keys and then copy those over from the main dict
        # into a new one
        if left is None:
            return right
        intersection = set(left.keys()).intersection(right.keys())
        # left and right have the same keys
        return {k: left[k] for k in intersection}

    def execute_action(self, node: AbstractNode, verify_key: VerifyKey) -> None:
        method = node.lib_ast(self.path)

        result_read_permissions = None

        resolved_args = list()
        for arg in self.args:
            if not isinstance(arg, Pointer):
                raise ValueError(
                    f"args attribute of RunFunctionOrConstructorAction should only contain Pointers. "
                    f"Got {arg} of type {type(arg)}"
                )

            r_arg = node.store.get_object(id=arg.id_at_location)
            result_read_permissions = self.intersect_keys(
                result_read_permissions, r_arg.read_permissions
            )
            resolved_args.append(r_arg.data)

        resolved_kwargs = {}
        for arg_name, arg in self.kwargs.items():
            if not isinstance(arg, Pointer):
                raise ValueError(
                    f"kwargs attribute of RunFunctionOrConstructorAction should only contain Pointers. "
                    f"Got {arg} of type {type(arg)}"
                )

            r_arg = node.store.get_object(id=arg.id_at_location)
            result_read_permissions = self.intersect_keys(
                result_read_permissions, r_arg.read_permissions
            )
            resolved_kwargs[arg_name] = r_arg.data

        result = method(*resolved_args, **resolved_kwargs)
        # TODO reintroduce new primitive logic
        # if isprimitive(value=result):
        #     # Wrap in a PyPrimitive
        #     result = PyPrimitive(data=result, id=self.id_at_location)
        # else:
        # TODO: overload all methods to incorporate this automatically
        if hasattr(result, "id"):
            result.id = self.id_at_location

        if not isinstance(result, StorableObject):
            result = StorableObject(
                id=self.id_at_location,
                data=result,
                read_permissions=(
                    result_read_permissions
                    if result_read_permissions is not None
                    else {}
                ),
            )

        node.store.store(obj=result)

    @syft_decorator(typechecking=True)
    def _object2proto(self) -> RunFunctionOrConstructorAction_PB:
        """Returns a protobuf serialization of self.

        As a requirement of all objects which inherit from Serializable,
        this method transforms the current object into the corresponding
        Protobuf object so that it can be further serialized.

        :return: returns a protobuf object
        :rtype: RunFunctionOrConstructorAction_PB

        .. note::
            This method is purely an internal method. Please use object.serialize() or one of
            the other public serialization methods if you wish to serialize an
            object.
        """
        return RunFunctionOrConstructorAction_PB(
            path=self.path,
            args=[x.serialize() for x in self.args],
            kwargs={k: v.serialize() for k, v in self.kwargs.items()},
            id_at_location=self.id_at_location.serialize(),
            address=self.address.serialize(),
            msg_id=self.id.serialize(),
        )

    @staticmethod
    def _proto2object(
        proto: RunFunctionOrConstructorAction_PB,
    ) -> "RunFunctionOrConstructorAction":
        """Creates a ObjectWithID from a protobuf

        As a requirement of all objects which inherit from Serializable,
        this method transforms a protobuf object into an instance of this class.

        :return: returns an instance of RunFunctionOrConstructorAction
        :rtype: RunFunctionOrConstructorAction

        .. note::
            This method is purely an internal method. Please use syft.deserialize()
            if you wish to deserialize an object.
        """

        return RunFunctionOrConstructorAction(
            path=proto.path,
            args=tuple(_deserialize(blob=x) for x in proto.args),
            kwargs={k: _deserialize(blob=v) for k, v in proto.kwargs.items()},
            id_at_location=_deserialize(blob=proto.id_at_location),
            address=_deserialize(blob=proto.address),
            msg_id=_deserialize(blob=proto.msg_id),
        )

    @staticmethod
    def get_protobuf_schema() -> GeneratedProtocolMessageType:
        """Return the type of protobuf object which stores a class of this type

        As a part of serialization and deserialization, we need the ability to
        lookup the protobuf object type directly from the object type. This
        static method allows us to do this.

        Importantly, this method is also used to create the reverse lookup ability within
        the metaclass of Serializable. In the metaclass, it calls this method and then
        it takes whatever type is returned from this method and adds an attribute to it
        with the type of this class attached to it. See the MetaSerializable class for details.

        :return: the type of protobuf object which corresponds to this class.
        :rtype: GeneratedProtocolMessageType

        """

        return RunFunctionOrConstructorAction_PB
