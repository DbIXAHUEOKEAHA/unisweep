from pymeasure.instruments.srs import SR860
from pymeasure.instruments.validators import strict_discrete_set, \
    truncated_discrete_set, truncated_range

import pyvisa as visa

import logging
import numpy as np
import time
from inspect import getmembers
from warnings import warn

from pymeasure.instruments import Instrument
from pymeasure.adapters import VISAAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    #return np.round(np.random.random(1), 1) #to test the program without device it would return random numbers
    return device.query(command)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class DynamicProperty(property):
    """ Class that allows managing python property behaviour in a "dynamic" fashion

    The class allows passing, in addition to regular property parameters, a list of
    runtime configurable parameters.
    The effect is that the behaviour of fget/fset not only depends on the obj parameter, but
    also on a set of keyword parameters with a default value.
    These extra parameters are read from instance, if available, or left with the default value.
    Dynamic behaviour is achieved by changing class or instance variables with special names
    defined as `<prefix> + <property name> + <param name>`.

    Code has been based on Python equivalent implementation of properties provided in the
    python documentation `here <https://docs.python.org/3/howto/descriptor.html#properties>`_.

    :param fget: class property fget parameter whose signature is expanded with a
                 set of keyword arguments as in fget_params_list
    :param fset: class property fget parameter whose signature is expanded with a
                 set of keyword arguments as in fset_params_list
    :param fdel: class property fdel parameter
    :param doc: class property doc parameter
    :param fget_params_list: List of parameter names that are dynamically configurable
    :param fset_params_list: List of parameter names that are dynamically configurable
    :param prefix: String to be prefixed to get dynamically configurable
                   parameters.
    """

    def __init__(self, fget=None, fset=None, fdel=None, doc=None, fget_params_list=None,
                 fset_params_list=None, prefix=""):
        super().__init__(fget, fset, fdel, doc)
        self.fget_params_list = () if fget_params_list is None else fget_params_list
        self.fset_params_list = () if fset_params_list is None else fset_params_list
        self.name = ""
        self.prefix = prefix

    def __get__(self, obj, objtype=None):
        if obj is None:
            # Property return itself when invoked from a class
            return self
        if self.fget is None:
            raise AttributeError(f"Unreadable attribute {self.name}")

        kwargs = {}
        for attr in self.fget_params_list:
            attr_instance_name = self.prefix + "_".join([self.name, attr])
            if hasattr(obj, attr_instance_name):
                kwargs[attr] = getattr(obj, attr_instance_name)
        return self.fget(obj, **kwargs)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError(f"Can't set attribute {self.name}")
        kwargs = {}
        for attr in self.fset_params_list:
            attr_instance_name = self.prefix + "_".join([self.name, attr])
            if hasattr(obj, attr_instance_name):
                kwargs[attr] = getattr(obj, attr_instance_name)
        self.fset(obj, value, **kwargs)

    def __set_name__(self, owner, name):
        self.name = name

class my_CommonBase:
    
    """Base class for instruments and channels.

    This class contains everything needed for pymeasure's property creator
    :meth:`control` and its derivatives :meth:`measurement` and :meth:`setting`.

    :param preprocess_reply: An optional callable used to preprocess
        strings received from the instrument. The callable returns the
        processed string.

        .. deprecated:: 0.11
            Implement it in the instrument's `read` method instead.
    """

    # Variable holding the list of DynamicProperty parameters that are configurable
    # by users
    _fget_params_list = ('get_command',
                         'values',
                         'map_values',
                         'get_process',
                         'command_process',
                         'check_get_errors')

    _fset_params_list = ('set_command',
                         'validator',
                         'values',
                         'map_values',
                         'set_process',
                         'command_process',
                         'check_set_errors')

    # Prefix used to store reserved variables
    __reserved_prefix = "___"

    def __init__(self, preprocess_reply=None, **kwargs):
        self._special_names = self._setup_special_names()
        self._create_channels()
        if preprocess_reply is not None:
            warn(("Parameter `preprocess_reply` is deprecated. "
                  "Implement it in the instrument, e.g. in `read`, instead."),
                 FutureWarning)
        self.preprocess_reply = preprocess_reply
        super().__init__(**kwargs)

    class BaseChannelCreator:
        """Base class for ChannelCreator and MultiChannelCreator.

        :param cls: Class for all children or tuple/list of classes, one for each child.
        :param \\**kwargs: Keyword arguments for all children.
        """

        def __init__(self, cls, **kwargs):
            try:
                self.valid_class = issubclass(cls, my_CommonBase)
            except TypeError:
                self.valid_class = False
            self.pairs = ()
            self.kwargs = kwargs

    class ChannelCreator(BaseChannelCreator):
        """Add a single channel to the parent class.

        The child will be added to the parent instance at instantiation with
        :func:`CommonBase.add_child`. The attribute name that ChannelCreator was assigned
        to in the `Instrument` class will be the name of the channel interface.

        .. code::

            class Extreme5000(Instrument):
                # Two output channels, accessible by their property names
                # and both are accessible through the 'channels' collection
                output_A = Instrument.ChannelCreator(Extreme5000Channel, "A")
                output_B = Instrument.ChannelCreator(Extreme5000Channel, "B")
                # A channel without a channel accessible through the 'motor' collection
                motor = Instrument.ChannelCreator(MotorControl)

            inst = SomeInstrument()
            # Set the extreme_temp for channel A of Extreme5000 instrument
            inst.output_A.extreme_temp = 42

        :param cls: Channel class for channel interface
        :param id: The id of the channel on the instrument, integer or string.
        :param \\**kwargs: Keyword arguments for all children.
        """

        def __init__(self, cls, id=None, **kwargs):
            super().__init__(cls=cls, **kwargs)
            if (isinstance(id, (str, int)) or id is None) and self.valid_class:
                self.pairs = ((cls, id),)
            else:
                raise ValueError("Invalid definition of class '{cls}' and id '{id}'.")

    class MultiChannelCreator(BaseChannelCreator):
        """Add channels to the parent class.

        The children will be added to the parent instance at instantiation with
        :func:`CommonBase.add_child`. The attribute name (e.g. :code:`channels`) will be
        used as the `collection` of the children. You may define the attribute
        prefix. If there are no other pressing reasons, use :code:`channels` as the attribute name
        and leave the prefix at the default :code:`"ch_"`.

        .. code::

            class Extreme5000(Instrument):
                # Three channels of the same type: 'ch_A', 'ch_B', 'ch_C'
                # and add them to the 'channels' collection
                channels = Instrument.MultiChannelCreator(Extreme5000Channel, ["A", "B", "C"])
                # Two channel interfaces of different types: 'fn_power', 'fn_voltage'
                # and add them to the 'functions' collection
                functions = Instrument.MultiChannelCreator((PowerChannel, VoltageChannel),
                                                ["power", "voltage"], prefix="fn_")

        :param cls: Class for all children or tuple/list of classes, one for each child.
        :param id: tuple/list of ids of the channels on the instrument.
        :param prefix: Collection prefix for the attributes, e.g. `"ch_"`
            creates attribute `self.ch_A`. If prefix evaluates False,
            the child will be added directly under the variable name. Required if id is tuple/list.
        :param \\**kwargs: Keyword arguments for all children.
        """

        def __init__(self, cls, id=None, prefix="ch_", **kwargs):
            super().__init__(cls=cls, **kwargs)
            if isinstance(id, (list, tuple)) and isinstance(cls, (list, tuple)):
                assert (len(id) == len(cls)), "Lengths of cls and id do not match."
                self.pairs = list(zip(cls, id))
            elif isinstance(id, (list, tuple)) and self.valid_class:
                self.pairs = list(zip((cls,) * len(id), id))
            else:
                raise ValueError("Invalid definition of classes '{cls}' and ids '{id}'.")
            self.kwargs.setdefault("prefix", prefix)

    def _setup_special_names(self):
        """ Return list of class/instance special names.

        Compute the list of special names based on the list of
        class attributes that are a DynamicProperty. Check also for class variables
        with special name and copy them at instance level
        Internal method, not intended to be accessed at user level."""
        special_names = []
        dynamic_params = tuple(set(self._fget_params_list + self._fset_params_list))
        # Check whether class variables of DynamicProperty type are present
        for attr_name, attr in getmembers(self.__class__):
            if isinstance(attr, DynamicProperty):
                special_names += [attr_name + "_" + key for key in dynamic_params]
        # Check if special variables are defined at class level
        for attr, value in getmembers(self.__class__):
            if attr in special_names:
                # Copy class special variable at instance level, prefixing reserved_prefix
                setattr(self, self.__reserved_prefix + attr, value)
        return special_names

    @staticmethod
    def get_channels(cls):
        """Return a list of all the Instrument's ChannelCreator and MultiChannelCreator instances"""
        class_members = getmembers(cls)

        channels = []
        for name, member in class_members:
            if isinstance(member, my_CommonBase.BaseChannelCreator):
                channels.append((name, member))
        return channels

    @staticmethod
    def get_channel_pairs(cls):
        """Return a list of all the Instrument's channel pairs"""
        channel_pairs = []
        for name, creator in my_CommonBase.get_channels(cls):
            for pair in creator.pairs:
                channel_pairs.append(pair)
        return channel_pairs

    def _create_channels(self):
        """Create channel interfaces for all the Instrument's channel pairs."""
        for name, creator in my_CommonBase.get_channels(self.__class__):
            for cls, id in creator.pairs:
                # If channel pair was created with MultiChannelCreator
                # add channel interface to collection with passed attribute name
                if isinstance(creator, my_CommonBase.MultiChannelCreator):
                    child = self.add_child(cls, id, collection=name, **creator.kwargs)
                # If channel pair was created with ChannelCreator
                # name channel interface with passed attribute name
                elif isinstance(creator, my_CommonBase.ChannelCreator):
                    child = self.add_child(cls, id, attr_name=name, **creator.kwargs)
                else:
                    raise ValueError("Invalid class '{creator}' for channel creation.")
                child._protected = True

    def __setattr__(self, name, value):
        """ Add reserved_prefix in front of special variables."""
        if hasattr(self, '_special_names'):
            if name in self._special_names:
                name = self.__reserved_prefix + name
        super().__setattr__(name, value)

    def __getattribute__(self, name):
        """ Prevent read access to variables with special names used to
        support dynamic property behaviour."""
        if name in ('_special_names', '__dict__'):
            return super().__getattribute__(name)
        if hasattr(self, '_special_names'):
            if name in self._special_names:
                raise AttributeError(
                    f"{name} is a reserved variable name and it cannot be read")
        return super().__getattribute__(name)

    # Channel management
    def add_child(self, cls, id=None, collection="channels", prefix="ch_", attr_name="", **kwargs):
        """Add a child to this instance and return its index in the children list.

        The newly created child may be accessed either by the id in the
        children dictionary or by the created attribute, e.g. the fifth channel of `instrument`
        with id "F" has two access options:
        :code:`instrument.channels["F"] == instrument.ch_F`

        .. note::

            Do not change the default `collection` or `prefix` parameter, unless
            you have to distinguish several collections of different children,
            e.g. different channel types (analog and digital).

        :param cls: Class of the channel.
        :param id: Child id how it is used in communication, e.g. `"A"`.
        :param collection: Name of the collection of children, used for dictionary access to the
            channel interfaces.
        :param prefix: For creating multiple channel interfaces, the prefix e.g. `"ch_"`
            is prepended to the attribute name of the channel interface `self.ch_A`.
            If prefix evaluates False, the child will be added directly under the collection name.
        :param attr_name: For creating a single channel interface, the attr_name argument is used
            when setting the attribute name of the channel interface.
        :param \\**kwargs: Keyword arguments for the channel creator.
        :returns: Instance of the created child.
        """
        child = cls(self, id, **kwargs)
        collection_data = getattr(self, collection, {})
        if isinstance(collection_data, my_CommonBase.BaseChannelCreator):
            collection_data = {}
        # Create channel interface if prefix or name is present
        if (prefix or attr_name) and id is not None:
            if not collection_data:
                # Add a grouplist to the parent.
                setattr(self, collection, collection_data)
            collection_data[id] = child
            child._collection = collection
            if attr_name:
                setattr(self, attr_name, child)
                child._name = attr_name
            else:
                setattr(self, f"{prefix}{id}", child)
                child._name = f"{prefix}{id}"
        elif attr_name and id is None:
            # If attribute name is passed with no channel id
            # set the child to the attribute name.
            setattr(self, attr_name, child)
            child._name = attr_name
        else:
            if collection_data:
                raise ValueError(f"An attribute '{collection}' already exists.")
            setattr(self, collection, child)
            child._name = collection
        return child

    def remove_child(self, child):
        """Remove the child from the instrument and the corresponding collection.

        :param child: Instance of the child to delete.
        """
        if hasattr(child, "_protected"):
            raise TypeError("You cannot remove channels defined at class level.")
        if hasattr(child, "_collection"):
            collection = getattr(self, child._collection)
            del collection[child.id]
        delattr(self, child._name)

    # Communication functions
    def wait_for(self, query_delay=0):
        """Wait for some time. Used by 'ask' to wait before reading.

        Implement in subclass!

        :param query_delay: Delay between writing and reading in seconds.
        """
        raise NotImplementedError("Implement in subclass!")

    def ask(self, command, query_delay=0):
        """Write a command to the instrument and return the read response.

        :param command: Command string to be sent to the instrument.
        :param query_delay: Delay between writing and reading in seconds.
        :returns: String returned by the device without read_termination.
        """
        self.write(command)
        self.wait_for(query_delay)
        return self.read()

    def values(self, command, separator=',', cast=float, preprocess_reply=None, maxsplit=-1,
               **kwargs):
        """Write a command to the instrument and return a list of formatted
        values from the result.

        :param command: SCPI command to be sent to the instrument.
        :param preprocess_reply: Optional callable used to preprocess the string
            received from the instrument, before splitting it.
            The callable returns the processed string.
        :param separator: A separator character to split the string returned by
            the device into a list.
        :param maxsplit: The string returned by the device is splitted at most `maxsplit` times.
            -1 (default) indicates no limit.
        :param cast: A type to cast each element of the splitted string.
        :param \\**kwargs: Keyword arguments to be passed to the :meth:`ask` method.
        :returns: A list of the desired type, or strings where the casting fails.
        """
        results = self.ask(command, **kwargs).strip()
        if callable(preprocess_reply):
            results = preprocess_reply(results)
        elif callable(self.preprocess_reply):
            results = self.preprocess_reply(results)
        results = results.split(separator, maxsplit=maxsplit)
        for i, result in enumerate(results):
            try:
                if cast == bool:
                    # Need to cast to float first since results are usually
                    # strings and bool of a non-empty string is always True
                    results[i] = bool(float(result))
                else:
                    results[i] = cast(result)
            except Exception:
                results[i] = np.nan
        return results

    def binary_values(self, command, query_delay=0, **kwargs):
        """ Write a command to the instrument and return a numpy array of the binary data.

        :param command: Command to be sent to the instrument.
        :param query_delay: Delay between writing and reading in seconds.
        :param kwargs: Arguments for :meth:`~pymeasure.Adapter.read_binary_values`.
        :returns: NumPy array of values.
        """
        self.write(command)
        self.wait_for(query_delay)
        return self.read_binary_values(**kwargs)

    # Property creators
    @staticmethod
    def control(  # noqa: C901 accept that this is a complex method
        get_command,
        set_command,
        docs,
        validator=lambda v, vs: v,
        values=(),
        map_values=False,
        get_process=lambda v: v,
        set_process=lambda v: v,
        command_process=None,
        check_set_errors=False,
        check_get_errors=False,
        dynamic=False,
        preprocess_reply=None,
        separator=',',
        maxsplit=-1,
        cast=float,
        values_kwargs=None,
        **kwargs
    ):
        """Return a property for the class based on the supplied
        commands. This property may be set and read from the
        instrument. See also :meth:`measurement` and :meth:`setting`.

        :param get_command: A string command that asks for the value, set to `None`
            if get is not supported (see also :meth:`setting`).
        :param set_command: A string command that writes the value, set to `None`
            if set is not supported (see also :meth:`measurement`).
        :param docs: A docstring that will be included in the documentation
        :param validator: A function that takes both a value and a group of valid values
            and returns a valid value, while it otherwise raises an exception
        :param values: A list, tuple, range, or dictionary of valid values, that can be used
            as to map values if :code:`map_values` is True.
        :param map_values: A boolean flag that determines if the values should be
            interpreted as a map
        :param get_process: A function that take a value and allows processing
            before value mapping, returning the processed value
        :param set_process: A function that takes a value and allows processing
            before value mapping, returning the processed value
        :param command_process: A function that takes a command and allows processing
            before executing the command

            .. deprecated:: 0.12
                Use a dynamic property instead.

        :param check_set_errors: Toggles checking errors after setting
        :param check_get_errors: Toggles checking errors after getting
        :param dynamic: Specify whether the property parameters are meant to be changed in
            instances or subclasses.
        :param preprocess_reply: Optional callable used to preprocess the string
            received from the instrument, before splitting it.
            The callable returns the processed string.
        :param separator: A separator character to split the string returned by
            the device into a list.
        :param maxsplit: The string returned by the device is splitted at most `maxsplit` times.
            -1 (default) indicates no limit.
        :param cast: A type to cast each element of the splitted string.
        :param dict values_kwargs: Further keyword arguments for :meth:`values`.
        :param \\**kwargs: Keyword arguments for :meth:`values`.

            .. deprecated:: 0.12
                Use `values_kwargs` dictionary parameter instead.

        Example of usage of dynamic parameter is as follows:

        .. code-block:: python

            class GenericInstrument(Instrument):
                center_frequency = Instrument.control(
                    ":SENS:FREQ:CENT?;", ":SENS:FREQ:CENT %e GHz;",
                    " A floating point property that represents the frequency ... ",
                    validator=strict_range,
                    # Redefine this in subclasses to reflect actual instrument value:
                    values=(1, 20),
                    dynamic=True  # enable changing property parameters on-the-fly
                )

            class SpecificInstrument(GenericInstrument):
                # Identical to GenericInstrument, except for frequency range
                # Override the "values" parameter of the "center_frequency" property
                center_frequency_values = (1, 10) # Redefined at subclass level

            instrument = SpecificInstrument()
            instrument.center_frequency_values = (1, 6e9) # Redefined at instance level

        .. warning:: Unexpected side effects when using dynamic properties

        Users must pay attention when using dynamic properties, since definition of class and/or
        instance attributes matching specific patterns could have unwanted side effect.
        The attribute name pattern `property_param`, where `property` is the name of the dynamic
        property (e.g. `center_frequency` in the example) and `param` is any of this method
        parameters name except `dynamic` and `docs` (e.g. `values` in the example) has to be
        considered reserved for dynamic property control.
        """
        if values_kwargs is None:
            values_kwargs = {}
        if kwargs:
            warn(f"Do not use keyword arguments {kwargs} as `control` parameter "
                 f"for the `values` method, use `values_kwargs` parameter instead. docs:\n{docs}",
                 FutureWarning)
            values_kwargs.update(kwargs)

        if command_process is None:
            command_process = lambda c: c  # noqa: E731
        else:
            warn("Do not use `command_process`, use a dynamic property instead.", FutureWarning)

        def fget(self,
                 get_command=get_command,
                 values=values,
                 map_values=map_values,
                 get_process=get_process,
                 command_process=command_process,
                 check_get_errors=check_get_errors,
                 ):
            if get_command is None:
                raise LookupError("Property can not be read.")
            vals = self.values(command_process(get_command),
                               separator=separator,
                               cast=cast,
                               preprocess_reply=preprocess_reply,
                               maxsplit=maxsplit,
                               **values_kwargs)
            if check_get_errors:
                try:
                    error_list = self.check_get_errors()
                except Exception as exc:
                    log.error("Exception raised while getting a property with the command "
                              f"""'{command_process(get_command)}': '{str(exc)}'.""")
                    raise
                errors = [str(error) for error in error_list]
                if errors:
                    log.error("Error received after trying to get a property with the command "
                              f"""'{command_process(get_command)}': '{"', '".join(errors)}'.""")
            if len(vals) == 1:
                value = get_process(vals[0])
                if not map_values:
                    return value
                elif isinstance(values, (list, tuple, range)):
                    return values[int(value)]
                elif isinstance(values, dict):
                    for k, v in values.items():
                        if v == value:
                            return k
                    raise KeyError(f"Value {value} not found in mapped values")
                else:
                    raise ValueError(
                        'Values of type `{}` are not allowed '
                        'for Instrument.control'.format(type(values))
                    )
            else:
                vals = get_process(vals)
                return vals

        def fset(self,
                 value,
                 set_command=set_command,
                 validator=validator,
                 values=values,
                 map_values=map_values,
                 set_process=set_process,
                 command_process=command_process,
                 check_set_errors=check_set_errors,
                 ):

            if set_command is None:
                raise LookupError("Property can not be set.")

            value = set_process(validator(value, values))
            if not map_values:
                pass
            elif isinstance(values, (list, tuple, range)):
                value = values.index(value)
            elif isinstance(values, dict):
                value = values[value]
            else:
                raise ValueError(
                    'Values of type `{}` are not allowed '
                    'for CommonBase.control'.format(type(values))
                )
            self.write(command_process(set_command) % value)
            if check_set_errors:
                try:
                    error_list = self.check_set_errors()
                except Exception as exc:
                    log.error("Exception raised while setting a property with the command "
                              f"""'{command_process(set_command) % value}': '{str(exc)}'.""")
                    raise
                errors = [str(error) for error in error_list]
                if errors:
                    log.error(
                        "Error received after trying to set a property with the command "
                        f"""'{command_process(set_command) % value}': '{"', '".join(errors)}'."""
                    )

        # Add the specified document string to the getter
        fget.__doc__ = docs

        if dynamic:
            fget.__doc__ += "(dynamic)"
            return DynamicProperty(fget=fget, fset=fset,
                                   fget_params_list=my_CommonBase._fget_params_list,
                                   fset_params_list=my_CommonBase._fset_params_list,
                                   prefix=my_CommonBase.__reserved_prefix)
        else:
            return property(fget, fset)

    @staticmethod
    def measurement(get_command, docs, values=(), map_values=None,
                    get_process=lambda v: v,
                    command_process=None,
                    check_get_errors=False, dynamic=False,
                    preprocess_reply=None,
                    separator=',',
                    maxsplit=-1,
                    cast=float,
                    values_kwargs=None,
                    **kwargs):
        """ Return a property for the class based on the supplied
        commands. This is a measurement quantity that may only be
        read from the instrument, not set.

        :param get_command: A string command that asks for the value
        :param docs: A docstring that will be included in the documentation
        :param values: A list, tuple, range, or dictionary of valid values, that can be used
            as to map values if :code:`map_values` is True.
        :param map_values: A boolean flag that determines if the values should be
            interpreted as a map
        :param get_process: A function that take a value and allows processing
            before value mapping, returning the processed value
        :param command_process: A function that take a command and allows processing
            before executing the command, for getting

            .. deprecated:: 0.12
                Use a dynamic property instead.

        :param check_get_errors: Toggles checking errors after getting
        :param dynamic: Specify whether the property parameters are meant to be changed in
            instances or subclasses. See :meth:`control` for an usage example.
        :param preprocess_reply: Optional callable used to preprocess the string
            received from the instrument, before splitting it.
            The callable returns the processed string.
        :param separator: A separator character to split the string returned by
            the device into a list.
        :param maxsplit: The string returned by the device is splitted at most `maxsplit` times.
            -1 (default) indicates no limit.
        :param cast: A type to cast each element of the splitted string.
        :param dict values_kwargs: Further keyword arguments for :meth:`values`.
        :param \\**kwargs: Keyword arguments for :meth:`values`.

            .. deprecated:: 0.12
                Use `values_kwargs` dictionary parameter instead.
        """
        if values_kwargs is None:
            values_kwargs = {}
        if kwargs:
            warn(f"Do not use keyword arguments {kwargs} as `measurement` parameter "
                 f"for the `values` method, use `values_kwargs` parameter instead. docs:\n{docs}",
                 FutureWarning)
            values_kwargs.update(kwargs)

        return my_CommonBase.control(get_command=get_command,
                                  set_command=None,
                                  docs=docs,
                                  values=values,
                                  map_values=map_values,
                                  get_process=get_process,
                                  command_process=command_process,
                                  check_get_errors=check_get_errors,
                                  dynamic=dynamic,
                                  preprocess_reply=preprocess_reply,
                                  separator=separator,
                                  maxsplit=maxsplit,
                                  cast=cast,
                                  values_kwargs=values_kwargs,
                                  )

    @staticmethod
    def setting(set_command, docs,
                validator=lambda x, y: x, values=(), map_values=False,
                set_process=lambda v: v,
                check_set_errors=False, dynamic=False,
                ):
        """Return a property for the class based on the supplied
        commands. This property may be set, but raises an exception
        when being read from the instrument.

        :param set_command: A string command that writes the value
        :param docs: A docstring that will be included in the documentation
        :param validator: A function that takes both a value and a group of valid values
            and returns a valid value, while it otherwise raises an exception
        :param values: A list, tuple, range, or dictionary of valid values, that can be used
            as to map values if :code:`map_values` is True.
        :param map_values: A boolean flag that determines if the values should be
            interpreted as a map
        :param set_process: A function that takes a value and allows processing
            before value mapping, returning the processed value
        :param check_set_errors: Toggles checking errors after setting
        :param dynamic: Specify whether the property parameters are meant to be changed in
            instances or subclasses. See :meth:`control` for an usage example.
        """

        return my_CommonBase.control(get_command=None,
                                  set_command=set_command,
                                  docs=docs,
                                  validator=validator,
                                  values=values,
                                  map_values=map_values,
                                  set_process=set_process,
                                  check_set_errors=check_set_errors,
                                  dynamic=dynamic,
                                  )

    def check_errors(self):
        """Read all errors from the instrument and log them.

        :return: List of error entries.
        """
        raise NotImplementedError("Implement it in a subclass.")

    def check_get_errors(self):
        """Check for errors after having gotten a property and log them.

        Called if :code:`check_get_errors=True` is set for that property.

        If you override this method, you may choose to raise an Exception for certain errors.

        :return: List of error entries.
        """
        raise NotImplementedError("Implement it in a subclass.")

    def check_set_errors(self):
        """Check for errors after having set a property and log them.

        Called if :code:`check_set_errors=True` is set for that property.

        If you override this method, you may choose to raise an Exception for certain errors.

        :return: List of error entries.
        """
        raise NotImplementedError("Implement it in a subclass.")


class my_Instrument(my_CommonBase):
    """ The base class for all Instrument definitions.

    It makes use of one of the :py:class:`~pymeasure.adapters.Adapter` classes for communication
    with the connected hardware device. This decouples the instrument/command definition from the
    specific communication interface used.

    When ``adapter`` is a string, this is taken as an appropriate resource name. Depending on your
    installed VISA library, this can be something simple like ``COM1`` or ``ASRL2``, or a more
    complicated
    `VISA resource name <https://pyvisa.readthedocs.io/en/latest/introduction/names.html>`__
    defining the target of your connection.

    When ``adapter`` is an integer, a GPIB resource name is created based on that.
    In either case a :py:class:`~pymeasure.adapters.VISAAdapter` is constructed based on that
    resource name.
    Keyword arguments can be used to further configure the connection.

    Otherwise, the passed :py:class:`~pymeasure.adapters.Adapter` object is used and any keyword
    arguments are discarded.

    This class defines basic SCPI commands by default. This can be disabled with
    :code:`includeSCPI` for instruments not compatible with the standard SCPI commands.

    :param adapter: A string, integer, or :py:class:`~pymeasure.adapters.Adapter` subclass object
    :param string name: The name of the instrument. Often the model designation by default.
    :param includeSCPI: A boolean, which toggles the inclusion of standard SCPI commands
    :param preprocess_reply: An optional callable used to preprocess
        strings received from the instrument. The callable returns the
        processed string.

        .. deprecated:: 0.11
            Implement it in the instrument's `read` method instead.
    :param \\**kwargs: In case ``adapter`` is a string or integer, additional arguments passed on
        to :py:class:`~pymeasure.adapters.VISAAdapter` (check there for details).
        Discarded otherwise.
    """

    # noinspection PyPep8Naming
    def __init__(self, adapter, name, includeSCPI=True,
                 preprocess_reply=None,
                 **kwargs):
        # Setup communication before possible children require the adapter.
        if isinstance(adapter, (int, str)):
            try:
                adapter = VISAAdapter(adapter, **kwargs)
            except ImportError:
                raise Exception("Invalid Adapter provided for Instrument since"
                                " PyVISA is not present")
        self.adapter = adapter
        self.SCPI = includeSCPI
        self.isShutdown = False
        self.name = name

        super().__init__(preprocess_reply=preprocess_reply)

        log.info("Initializing %s." % self.name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    # SCPI default properties
    @property
    def complete(self):
        """Get the synchronization bit.

        This property allows synchronization between a controller and a device. The Operation
        Complete query places an ASCII character 1 into the device's Output Queue when all pending
        selected device operations have been finished.
        """
        if self.SCPI:
            return self.ask("*OPC?").strip()
        else:
            raise NotImplementedError("Non SCPI instruments require implementation in subclasses")

    @property
    def status(self):
        """ Get the status byte and Master Summary Status bit. """
        if self.SCPI:
            return self.ask("*STB?").strip()
        else:
            raise NotImplementedError("Non SCPI instruments require implementation in subclasses")

    @property
    def options(self):
        """ Get the device options installed. """
        if self.SCPI:
            return self.ask("*OPT?").strip()
        else:
            raise NotImplementedError("Non SCPI instruments require implementation in subclasses")

    @property
    def id(self):
        """ Get the identification of the instrument. """
        if self.SCPI:
            return self.ask("*IDN?").strip()
        else:
            raise NotImplementedError("Non SCPI instruments require implementation in subclasses")

    # Wrapper functions for the Adapter object
    def write(self, command, **kwargs):
        """Write a string command to the instrument appending `write_termination`.

        :param command: command string to be sent to the instrument
        :param kwargs: Keyword arguments for the adapter.
        """
        self.adapter.write(command, **kwargs)

    def write_bytes(self, content, **kwargs):
        """Write the bytes `content` to the instrument."""
        self.adapter.write_bytes(content, **kwargs)

    def read(self, **kwargs):
        """Read up to (excluding) `read_termination` or the whole read buffer."""
        return self.adapter.read(**kwargs)

    def read_bytes(self, count, **kwargs):
        """Read a certain number of bytes from the instrument.

        :param int count: Number of bytes to read. A value of -1 indicates to
            read the whole read buffer.
        :param kwargs: Keyword arguments for the adapter.
        :returns bytes: Bytes response of the instrument (including termination).
        """
        return self.adapter.read_bytes(count, **kwargs)

    def write_binary_values(self, command, values, *args, **kwargs):
        """Write binary values to the device.

        :param command: Command to send.
        :param values: The values to transmit.
        :param \\*args, \\**kwargs: Further arguments to hand to the Adapter.
        """
        self.adapter.write_binary_values(command, values, *args, **kwargs)

    def read_binary_values(self, **kwargs):
        """Read binary values from the device."""
        return self.adapter.read_binary_values(**kwargs)

    # Communication functions
    def wait_for(self, query_delay=0):
        """Wait for some time. Used by 'ask' to wait before reading.

        :param query_delay: Delay between writing and reading in seconds.
        """
        if query_delay:
            time.sleep(query_delay)

    # SCPI default methods
    def clear(self):
        """ Clears the instrument status byte
        """
        if self.SCPI:
            self.write("*CLS")
        else:
            raise NotImplementedError("Non SCPI instruments require implementation in subclasses")

    def reset(self):
        """ Resets the instrument. """
        if self.SCPI:
            self.write("*RST")
        else:
            raise NotImplementedError("Non SCPI instruments require implementation in subclasses")

    def shutdown(self):
        """Brings the instrument to a safe and stable state"""
        self.isShutdown = True
        log.info(f"Finished shutting down {self.name}")

    def check_errors(self):
        """Read all errors from the instrument and log them.

        :return: List of error entries.
        """
        if self.SCPI:
            errors = []
            while True:
                err = self.values("SYST:ERR?")
                if int(err[0]) != 0:
                    log.error(f"{self.name}: {err[0]}, {err[1]}")
                    errors.append(err)
                else:
                    break
            return errors
        else:
            raise NotImplementedError("Non SCPI instruments require implementation in subclasses")

    def check_get_errors(self):
        """Check for errors after having gotten a property and log them.

        Called if :code:`check_get_errors=True` is set for that property.

        If you override this method, you may choose to raise an Exception for certain errors.

        :return: List of error entries.
        """
        return self.check_errors()

    def check_set_errors(self):
        """Check for errors after having set a property and log them.

        Called if :code:`check_set_errors=True` is set for that property.

        If you override this method, you may choose to raise an Exception for certain errors.

        :return: List of error entries.
        """
        return self.check_errors()

class new_SR860(my_Instrument):

    SENSITIVITIES = [
        1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
        500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
        200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
        50e-3, 100e-3, 200e-3, 500e-3, 1
    ]
    TIME_CONSTANTS = [
        1e-6, 3e-6, 10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3,
        30e-3, 100e-3, 300e-3, 1, 3, 10, 30, 100, 300, 1e3,
        3e3, 10e3, 30e3
    ]
    ON_OFF_VALUES = ['0', '1']
    SCREEN_LAYOUT_VALUES = ['0', '1', '2', '3', '4', '5']
    EXPANSION_VALUES = ['0', '1', '2,']
    CHANNEL_VALUES = ['OCH1', 'OCH2']
    OUTPUT_VALUES = ['XY', 'RTH']
    INPUT_TIMEBASE = ['AUTO', 'IN']
    INPUT_DCMODE = ['COM', 'DIF', 'common', 'difference']
    INPUT_REFERENCESOURCE = ['INT', 'EXT', 'DUAL', 'CHOP']
    INPUT_REFERENCETRIGGERMODE = ['SIN', 'POS', 'NEG', 'POSTTL', 'NEGTTL']
    INPUT_REFERENCEEXTERNALINPUT = ['50OHMS', '1MEG']
    INPUT_SIGNAL_INPUT = ['VOLT', 'CURR', 'voltage', 'current']
    INPUT_VOLTAGE_MODE = ['A', 'A-B']
    INPUT_COUPLING = ['AC', 'DC']
    INPUT_SHIELDS = ['Float', 'Ground']
    INPUT_RANGE = ['1V', '300M', '100M', '30M', '10M']
    INPUT_GAIN = ['1MEG', '100MEG']
    INPUT_FILTER = ['Off', 'On']
    LIST_PARAMETER = ['i=', '0=Xoutput', '1=Youtput', '2=Routput', 'Thetaoutput', '4=Aux IN1',
                      '5=Aux IN2', '6=Aux IN3', '7=Aux IN4', '8=Xnoise', '9=Ynoise',
                      '10=AUXOut1', '11=AuxOut2', '12=Phase', '13=Sine Out amplitude',
                      '14=DCLevel', '15I=nt.referenceFreq', '16=Ext.referenceFreq']
    LIST_HORIZONTAL_TIME_DIV = ['0=0.5s', '1=1s', '2=2s', '3=5s', '4=10s', '5=30s', '6=1min',
                                '7=2min', '8=5min', '9=10min', '10=30min', '11=1hour', '12=2hour',
                                '13=6hour', '14=12hour', '15=1day', '16=2days']

    x = my_Instrument.measurement("OUTP? 0",
                               """ Reads the X value in Volts """
                               )
    y = my_Instrument.measurement("OUTP? 1",
                               """ Reads the Y value in Volts """
                               )
    magnitude = my_Instrument.measurement("OUTP? 2",
                                       """ Reads the magnitude in Volts. """
                                       )
    theta = my_Instrument.measurement("OUTP? 3",
                                   """ Reads the theta value in degrees. """
                                   )
    phase = my_Instrument.control(
        "PHAS?", "PHAS %0.7f",
        """ A floating point property that represents the lock-in phase
        in degrees. This property can be set. """,
        validator=truncated_range,
        values=[-360, 360]
    )
    frequency = my_Instrument.control(
        "FREQ?", "FREQ %0.6e",
        """ A floating point property that represents the lock-in frequency
        in Hz. This property can be set. """,
        validator=truncated_range,
        values=[0.001, 500000]
    )
    internalfrequency = my_Instrument.control(
        "FREQINT?", "FREQINT %0.6e",
        """A floating property that represents the internal lock-in frequency in Hz
        This property can be set.""",
        validator=truncated_range,
        values=[0.001, 500000]
    )
    harmonic = my_Instrument.control(
        "HARM?", "Harm %d",
        """An integer property that controls the harmonic that is measured.
        Allowed values are 1 to 99. Can be set.""",
        validator=strict_discrete_set,
        values=range(1, 99)
    )
    harmonicdual = my_Instrument.control(
        "HARMDUAL?", "HARMDUAL %d",
        """An integer property that controls the harmonic in dual reference mode that is measured.
        Allowed values are 1 to 99. Can be set.""",
        validator=strict_discrete_set,
        values=range(1, 99)
    )
    sine_voltage = my_Instrument.control(
        "SLVL?", "SLVL %0.9e",
        """A floating point property that represents the reference sine-wave
        voltage in Volts. This property can be set.""",
        validator=truncated_range,
        values=[1e-9, 2]
    )

    timebase = my_Instrument.control(
        "TBMODE?", "TBMODE %d",
        """Sets the external 10 MHZ timebase to auto(i=0) or internal(i=1).""",
        validator=strict_discrete_set,
        values=[0, 1],
        map_values=True
    )
    dcmode = my_Instrument.control(
        "REFM?", "REFM %d",
        """A string property that represents the sine out dc mode.
        This property can be set. Allowed values are:{}""".format(INPUT_DCMODE),
        validator=strict_discrete_set,
        values=INPUT_DCMODE,
        map_values=True
    )
    reference_source = my_Instrument.control(
        "RSRC?", "RSRC %d",
        """A string property that represents the reference source.
        This property can be set. Allowed values are:{}""".format(INPUT_REFERENCESOURCE),
        validator=strict_discrete_set,
        values=INPUT_REFERENCESOURCE,
        map_values=True
    )
    reference_triggermode = my_Instrument.control(
        "RTRG?", "RTRG %d",
        """A string property that represents the external reference trigger mode.
        This property can be set. Allowed values are:{}""".format(INPUT_REFERENCETRIGGERMODE),
        validator=strict_discrete_set,
        values=INPUT_REFERENCETRIGGERMODE,
        map_values=True
    )
    reference_externalinput = my_Instrument.control(
        "REFZ?", "REFZ&d",
        """A string property that represents the external reference input.
        This property can be set. Allowed values are:{}""".format(INPUT_REFERENCEEXTERNALINPUT),
        validator=strict_discrete_set,
        values=INPUT_REFERENCEEXTERNALINPUT,
        map_values=True
    )
    input_signal = my_Instrument.control(
        "IVMD?", "IVMD %d",
        """A string property that represents the signal input.
        This property can be set. Allowed values are:{}""".format(INPUT_SIGNAL_INPUT),
        validator=strict_discrete_set,
        values=INPUT_SIGNAL_INPUT,
        map_values=True
    )
    input_voltage_mode = my_Instrument.control(
        "ISRC?", "ISRC %d",
        """A string property that represents the voltage input mode.
        This property can be set. Allowed values are:{}""".format(INPUT_VOLTAGE_MODE),
        validator=strict_discrete_set,
        values=INPUT_VOLTAGE_MODE,
        map_values=True
    )
    input_coupling = my_Instrument.control(
        "ICPL?", "ICPL %d",
        """A string property that represents the input coupling.
        This property can be set. Allowed values are:{}""".format(INPUT_COUPLING),
        validator=strict_discrete_set,
        values=INPUT_COUPLING,
        map_values=True
    )
    input_shields = my_Instrument.control(
        "IGND?", "IGND %d",
        """A string property that represents the input shield grounding.
        This property can be set. Allowed values are:{}""".format(INPUT_SHIELDS),
        validator=strict_discrete_set,
        values=INPUT_SHIELDS,
        map_values=True
    )
    input_range = my_Instrument.control(
        "IRNG?", "IRNG %d",
        """A string property that represents the input range.
        This property can be set. Allowed values are:{}""".format(INPUT_RANGE),
        validator=strict_discrete_set,
        values=INPUT_RANGE,
        map_values=True
    )
    input_current_gain = my_Instrument.control(
        "ICUR?", "ICUR %d",
        """A string property that represents the current input gain.
        This property can be set. Allowed values are:{}""".format(INPUT_GAIN),
        validator=strict_discrete_set,
        values=INPUT_GAIN,
        map_values=True
    )
    sensitvity = my_Instrument.control(
        "SCAL?", "SCAL %d",
        """ A floating point property that controls the sensitivity in Volts,
        which can take discrete values from 2 nV to 1 V. Values are truncated
        to the next highest level if they are not exact. """,
        validator=truncated_discrete_set,
        values=SENSITIVITIES,
        map_values=True
    )
    time_constant = my_Instrument.control(
        "OFLT?", "OFLT %d",
        """ A floating point property that controls the time constant
        in seconds, which can take discrete values from 10 microseconds
        to 30,000 seconds. Values are truncated to the next highest
        level if they are not exact. """,
        validator=truncated_discrete_set,
        values=TIME_CONSTANTS,
        map_values=True
    )
    filter_slope = my_Instrument.control(
        "OFSL?", "OFSL %d",
        """A integer property that sets the filter slope to 6 dB/oct(i=0), 12 DB/oct(i=1),
        18 dB/oct(i=2), 24 dB/oct(i=3).""",
        validator=strict_discrete_set,
        values=range(0, 3)
    )
    filer_synchronous = my_Instrument.control(
        "SYNC?", "SYNC %d",
        """A string property that represents the synchronous filter.
        This property can be set. Allowed values are:{}""".format(INPUT_FILTER),
        validator=strict_discrete_set,
        values=INPUT_FILTER,
        map_values=True
    )
    filter_advanced = my_Instrument.control(
        "ADVFILT?", "ADVFIL %d",
        """A string property that represents the advanced filter.
        This property can be set. Allowed values are:{}""".format(INPUT_FILTER),
        validator=strict_discrete_set,
        values=INPUT_FILTER,
        map_values=True
    )
    frequencypreset1 = my_Instrument.control(
        "PSTF? 0", "PSTF 0, %0.6e",
        """A floating point property that represents the preset frequency for the F1 preset button.
        This property can be set.""",
        validator=truncated_range,
        values=[0.001, 500000]
    )
    frequencypreset2 = my_Instrument.control(
        "PSTF? 1", "PSTF 1, %0.6e",
        """A floating point property that represents the preset frequency for the F2 preset button.
        This property can be set.""",
        validator=truncated_range,
        values=[0.001, 500000]
    )
    frequencypreset3 = my_Instrument.control(
        "PSTF? 2", "PSTF2, %0.6e",
        """A floating point property that represents the preset frequency for the F3 preset button.
        This property can be set.""",
        validator=truncated_range,
        values=[0.001, 500000]
    )
    frequencypreset4 = my_Instrument.control(
        "PSTF? 3", "PSTF3, %0.6e",
        """A floating point property that represents the preset frequency for the F4 preset button.
        This property can be set.""",
        validator=truncated_range,
        values=[0.001, 500000]
    )
    sine_amplitudepreset1 = my_Instrument.control(
        "PSTA? 0", "PSTA0, %0.9e",
        """Floating point property representing the preset sine out amplitude, for the A1 preset button.
        This property can be set.""",  # noqa: E501
        validator=truncated_range,
        values=[1e-9, 2]
    )
    sine_amplitudepreset2 = my_Instrument.control(
        "PSTA? 1", "PSTA1, %0.9e",
        """Floating point property representing the preset sine out amplitude, for the A2 preset button.
        This property can be set.""",  # noqa: E501
        validator=truncated_range,
        values=[1e-9, 2]
    )
    sine_amplitudepreset3 = my_Instrument.control(
        "PSTA? 2", "PSTA2, %0.9e",
        """Floating point property representing the preset sine out amplitude, for the A3 preset button.
        This property can be set.""",  # noqa: E501
        validator=truncated_range,
        values=[1e-9, 2]
    )
    sine_amplitudepreset4 = my_Instrument.control(
        "PSTA? 3", "PSTA 3, %0.9e",
        """Floating point property representing the preset sine out amplitude, for the A3 preset button.
        This property can be set.""",  # noqa: E501
        validator=truncated_range,
        values=[1e-9, 2]
    )
    sine_dclevelpreset1 = my_Instrument.control(
        "PSTL? 0", "PSTL 0, %0.3e",
        """A floating point property that represents the preset sine out dc level for the L1 button.
        This property can be set.""",
        validator=truncated_range,
        values=[-5, 5]
    )
    sine_dclevelpreset2 = my_Instrument.control(
        "PSTL? 1", "PSTL 1, %0.3e",
        """A floating point property that represents the preset sine out dc level for the L2 button.
        This property can be set.""",
        validator=truncated_range,
        values=[-5, 5]
    )
    sine_dclevelpreset3 = my_Instrument.control(
        "PSTL? 2", "PSTL 2, %0.3e",
        """A floating point property that represents the preset sine out dc level for the L3 button.
        This property can be set.""",
        validator=truncated_range,
        values=[-5, 5]
    )
    sine_dclevelpreset4 = my_Instrument.control(
        "PSTL? 3", "PSTL3, %0.3e",
        """A floating point property that represents the preset sine out dc level for the L4 button.
        This property can be set.""",
        validator=truncated_range,
        values=[-5, 5]
    )

    aux_out_1 = my_Instrument.control(
        "AUXV? 0", "AUXV 1, %f",
        """ A floating point property that controls the output of Aux output 1 in
        Volts, taking values between -10.5 V and +10.5 V.
        This property can be set.""",
        validator=truncated_range,
        values=[-10.5, 10.5]
    )
    # For consistency with other lock-in my_Instrument classes
    dac1 = aux_out_1

    aux_out_2 = my_Instrument.control(
        "AUXV? 1", "AUXV 2, %f",
        """ A floating point property that controls the output of Aux output 2 in
        Volts, taking values between -10.5 V and +10.5 V.
        This property can be set.""",
        validator=truncated_range,
        values=[-10.5, 10.5]
    )
    # For consistency with other lock-in my_Instrument classes
    dac2 = aux_out_2

    aux_out_3 = my_Instrument.control(
        "AUXV? 2", "AUXV 3, %f",
        """ A floating point property that controls the output of Aux output 3 in
        Volts, taking values between -10.5 V and +10.5 V.
        This property can be set.""",
        validator=truncated_range,
        values=[-10.5, 10.5]
    )
    # For consistency with other lock-in my_Instrument classes
    dac3 = aux_out_3

    aux_out_4 = my_Instrument.control(
        "AUXV? 3", "AUXV 4, %f",
        """ A floating point property that controls the output of Aux output 4 in
        Volts, taking values between -10.5 V and +10.5 V.
        This property can be set.""",
        validator=truncated_range,
        values=[-10.5, 10.5]
    )
    # For consistency with other lock-in my_Instrument classes
    dac4 = aux_out_4

    aux_in_1 = my_Instrument.measurement(
        "OAUX? 0",
        """ Reads the Aux input 1 value in Volts with 1/3 mV resolution. """
    )
    # For consistency with other lock-in my_Instrument classes
    adc1 = aux_in_1

    aux_in_2 = my_Instrument.measurement(
        "OAUX? 1",
        """ Reads the Aux input 2 value in Volts with 1/3 mV resolution. """
    )
    # For consistency with other lock-in my_Instrument classes
    adc2 = aux_in_2

    aux_in_3 = my_Instrument.measurement(
        "OAUX? 2",
        """ Reads the Aux input 3 value in Volts with 1/3 mV resolution. """
    )
    # For consistency with other lock-in my_Instrument classes
    adc3 = aux_in_3

    aux_in_4 = my_Instrument.measurement(
        "OAUX? 3",
        """ Reads the Aux input 4 value in Volts with 1/3 mV resolution. """
    )
    # For consistency with other lock-in my_Instrument classes
    adc4 = aux_in_4

    def snap(self, val1="X", val2="Y", val3=None):
        """retrieve 2 or 3 parameters at once
        parameters can be chosen by index, or enumeration as follows:

        +--------+-------------+------------------------+
        | index  | enumeration | parameter              |
        +========+=============+========================+
        | 0      | X           | X output               |
        +--------+-------------+------------------------+
        | 1      | Y           | Y output               |
        +--------+-------------+------------------------+
        | 2      | R           | R output               |
        +--------+-------------+------------------------+
        | 3      | THeta       | θ output               |
        +--------+-------------+------------------------+
        | 4      | IN1         | Aux In1                |
        +--------+-------------+------------------------+
        | 5      | IN2         | Aux In2                |
        +--------+-------------+------------------------+
        | 6      | IN3         | Aux In3                |
        +--------+-------------+------------------------+
        | 7      | IN4         | Aux In4                |
        +--------+-------------+------------------------+
        | 8      | XNOise      | Xnoise                 |
        +--------+-------------+------------------------+
        | 9      | YNOise      | Ynoise                 |
        +--------+-------------+------------------------+
        | 10     | OUT1        | Aux Out1               |
        +--------+-------------+------------------------+
        | 11     | OUT2        | Aux Out2               |
        +--------+-------------+------------------------+
        | 12     | PHAse       | Reference Phase        |
        +--------+-------------+------------------------+
        | 13     | SAMp        | Sine Out Amplitude     |
        +--------+-------------+------------------------+
        | 14     | LEVel       | DC Level               |
        +--------+-------------+------------------------+
        | 15     | FInt        | Int. Ref. Frequency    |
        +--------+-------------+------------------------+
        | 16     | FExt        | Ext. Ref. Frequency    |
        +--------+-------------+------------------------+

        :param val1: parameter enumeration/index
        :param val2: parameter enumeration/index
        :param val3: parameter enumeration/index (optional)

        Defaults:
            val1 = "X"
            val2 = "Y"
            val3 = None
        """
        if val3 is None:
            return self.values(
                command=f"SNAP? {val1}, {val2}",
                separator=",",
                cast=float,
            )
        else:
            return self.values(
                command=f"SNAP? {val1}, {val2}, {val3}",
                separator=",",
                cast=float,
            )

    gettimebase = my_Instrument.measurement(
        "TBSTAT?",
        """Returns the current 10 MHz timebase source."""
    )
    extfreqency = my_Instrument.measurement(
        "FREQEXT?",
        """Returns the external frequency in Hz."""
    )
    detectedfrequency = my_Instrument.measurement(
        "FREQDET?",
        """Returns the actual detected frequency in HZ."""
    )
    get_signal_strength_indicator = my_Instrument.measurement(
        "ILVL?",
        """Returns the signal strength indicator."""
    )
    get_noise_bandwidth = my_Instrument.measurement(
        "ENBW?",
        """Returns the equivalent noise bandwidth, in hertz."""
    )
    # Display Commands
    front_panel = my_Instrument.control(
        "DBLK?", "DBLK %i",
        """Turns the front panel blanking on(i=0) or off(i=1).""",
        validator=strict_discrete_set,
        values=ON_OFF_VALUES,
        map_values=True
    )
    screen_layout = my_Instrument.control(
        "DLAY?", "DLAY %i",
        """A integer property that Sets the screen layout to trend(i=0), full strip chart
        history(i=1), half strip chart history(i=2), full FFT(i=3), half FFT(i=4) or big
        numerical(i=5).""",
        validator=strict_discrete_set,
        values=SCREEN_LAYOUT_VALUES,
        map_values=True
    )

    def screenshot(self):
        """Take screenshot on device
        The DCAP command saves a screenshot to a USB memory stick.
        This command is the same as pressing the [Screen Shot] key.
        A USB memory stick must be present in the front panel USB port.
        """
        self.write("DCAP")

    parameter_DAT1 = my_Instrument.control(
        "CDSP? 0", "CDSP 0, %i",
        """A integer property that assigns a parameter to data channel 1(green).
        This parameters can be set. Allowed values are:{}""".format(LIST_PARAMETER),
        validator=strict_discrete_set,
        values=range(0, 16)
    )
    parameter_DAT2 = my_Instrument.control(
        "CDSP? 1", "CDSP 1, %i",
        """A integer property that assigns a parameter to data channel 2(blue).
        This parameters can be set. Allowed values are:{}""".format(LIST_PARAMETER),
        validator=strict_discrete_set,
        values=range(0, 16)
    )
    parameter_DAT3 = my_Instrument.control(
        "CDSP? 2", "CDSP 2, %i",
        """A integer property that assigns a parameter to data channel 3(yellow).
        This parameters can be set. Allowed values are:{}""".format(LIST_PARAMETER),
        validator=strict_discrete_set,
        values=range(0, 16)
    )
    parameter_DAT4 = my_Instrument.control(
        "CDSP? 3", "CDSP 3, %i",
        """A integer property that assigns a parameter to data channel 3(orange).
        This parameters can be set. Allowed values are:{}""".format(LIST_PARAMETER),
        validator=strict_discrete_set,
        values=range(0, 16)
    )
    strip_chart_dat1 = my_Instrument.control(
        "CGRF? 0", "CGRF 0, %i",
        """A integer property that turns the strip chart graph of data channel 1 off(i=0) or on(i=1).
        """,  # noqa: E501
        validator=strict_discrete_set,
        values=ON_OFF_VALUES,
        map_values=True
    )
    strip_chart_dat2 = my_Instrument.control(
        "CGRF? 1", "CGRF 1, %i",
        """A integer property that turns the strip chart graph of data channel 2 off(i=0) or on(i=1).
        """,  # noqa: E501
        validator=strict_discrete_set,
        values=ON_OFF_VALUES,
        map_values=True
    )
    strip_chart_dat3 = my_Instrument.control(
        "CGRF? 2", "CGRF 2, %i",
        """A integer property that turns the strip chart graph of data channel 1 off(i=0) or on(i=1).
        """,  # noqa: E501
        validator=strict_discrete_set,
        values=ON_OFF_VALUES,
        map_values=True
    )
    strip_chart_dat4 = my_Instrument.control(
        "CGRF? 3", "CGRF 3, %i",
        """A integer property that turns the strip chart graph of data channel 4 off(i=0) or on(i=1).
        """,  # noqa: E501
        validator=strict_discrete_set,
        values=ON_OFF_VALUES,
        map_values=True
    )
    # Strip Chart commands
    horizontal_time_div = my_Instrument.control(
        "GSPD?", "GSDP %i",
        """A integer property for the horizontal time/div according to the following table:{}
        """.format(LIST_HORIZONTAL_TIME_DIV),
        validator=strict_discrete_set,
        values=range(0, 16)
    )

    def __init__(self, adapter, name="Stanford Research Systems SR860 Lock-in amplifier",
                 **kwargs):
        super().__init__(
            adapter,
            name,
            **kwargs
        )

class my_SR860(SR860):
    
    xnoize = my_Instrument.measurement("OUTP? 8",
                               """ Reads the Xnoise value in Volts """
                               )
    
    ynoize = my_Instrument.measurement("OUTP? 9",
                               """ Reads the Xnoise value in Volts """
                               )
    
    FFT = my_Instrument.measurement("FCRY?",
                               """ Reads the amplitude of FFT on the cursor position """
                               )
    
    DC_bias = my_Instrument.control(
        "SOFF?", "SOFF %0.9e",
        """A floating property that represents the lock-in DC bias offset in Volts
        This property can be set.""")
        
    IDN = my_Instrument.measurement("*IDN?",
                               """ Reads the Identification """
                               )

    SENSITIVITIES = [
        1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
        500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
        200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
        50e-3, 100e-3, 200e-3, 500e-3, 1
    ][::-1]

    sensitivity = my_Instrument.control(
        "SCAL?", "SCAL %d",
        """ A floating point property that controls the sensitivity in Volts,
        which can take discrete values from 2 nV to 1 V. Values are truncated
        to the next highest level if they are not exact. """,
        validator=truncated_discrete_set,
        values=SENSITIVITIES,
        map_values=True
    )
    
    INPUT_FILTER = ['Off', 'On']
    
    filter_synchronous = my_Instrument.control(
        "SYNC?", "SYNC %d",
        """A string property that represents the synchronous filter.
        This property can be set. Allowed values are:{}""".format(INPUT_FILTER),
        validator=strict_discrete_set,
        values=INPUT_FILTER,
        map_values=True
    )
    
    frequency = my_Instrument.control(
        "FREQ?", "FREQ %0.6e",
        """ A floating point property that represents the lock-in frequency
        in Hz. This property can be set. """,
        validator=truncated_range,
        values=[0.001, 4000000])
    
class sr860():

    def __init__(self, adress='GPIB0::3::INSTR'):

        self.sr860 = my_SR860(adress)
        self.adress = adress
        
        self.set_options = ['amplitude', 'frequency', 'phase', 'sensitivity', 
                            'time_constant', 'input_range', 'low_pass_filter_slope', 'synchronous_filter_status',
                            'AUX1_output', 'AUX2_output', 'AUX3_output', 'AUX4_output', 'PULS_AUX_1', 'dc_bias', 'Write']

        self.get_options = ['x', 'y', 'r', 'Θ', 'xnoize', 'ynoize', 'FFT', 'sensitivity', 
                            'time_constant', 'input_range', 'low_pass_filter_slope', 'synchronous_filter_status',
                            'AUX1_input', 'AUX2_input', 'AUX3_input', 'AUX4_input', 
                            'amplitude', 'frequency', 'phase', 'dc_bias', 'Read']
        
        self.SENSITIVITIES = [
            1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
            500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
            200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
            50e-3, 100e-3, 200e-3, 500e-3, 1
        ]
        self.TIME_CONSTANTS = [
            1e-6, 3e-6, 10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3,
            30e-3, 100e-3, 300e-3, 1, 3, 10, 30, 100, 300, 1e3,
            3e3, 10e3, 30e3
        ]
        self.ON_OFF_VALUES = ['0', '1']
        self.SCREEN_LAYOUT_VALUES = ['0', '1', '2', '3', '4', '5']
        self.EXPANSION_VALUES = ['0', '1', '2,']
        self.CHANNEL_VALUES = ['OCH1', 'OCH2']
        self.OUTPUT_VALUES = ['XY', 'RTH']
        self.INPUT_TIMEBASE = ['AUTO', 'IN']
        self.INPUT_DCMODE = ['COM', 'DIF', 'common', 'difference']
        self.INPUT_REFERENCESOURCE = ['INT', 'EXT', 'DUAL', 'CHOP']
        self.INPUT_REFERENCETRIGGERMODE = ['SIN', 'POS', 'NEG', 'POSTTL', 'NEGTTL']
        self.INPUT_REFERENCEEXTERNALINPUT = ['50OHMS', '1MEG']
        self.INPUT_SIGNAL_INPUT = ['VOLT', 'CURR', 'voltage', 'current']
        self.INPUT_VOLTAGE_MODE = ['A', 'A-B']
        self.INPUT_COUPLING = ['AC', 'DC']
        self.INPUT_SHIELDS = ['Float', 'Ground']
        self.INPUT_RANGE = ['1V', '300M', '100M', '30M', '10M']
        self.INPUT_GAIN = ['1MEG', '100MEG']
        self.INPUT_FILTER = ['Off', 'On']
        
        self.loggable = ['IDN', 'sensitivity', 'time_constant', 'frequency', 'phase',
                         'low_pass_filter_slope', 'synchronous_filter_status', 'dcmode', 
                         'reference_source', 'reference_triggermode', 'reference_externalinput',
                         'input_signal', 'input_voltage_mode', 'input_coupling', 'input_shields',
                         'input_range', 'input_current_gain', 'timebase', 'freq_ext', 
                         'freq_detected', 'signal_strength_indicator', 'noise_bandwidth']

    def IDN(self):
        return self.sr860.IDN
    
    def Write(self):
        return self.Read()
    
    def Read(self):
        device = rm.open_resource(
            self.adress)
        answer = device.read()
        device.close()
        return answer

    def x(self):
        ans = self.sr860.x
        return ans

    def y(self):
        ans = self.sr860.y
        return ans

    def r(self):
        return self.sr860.magnitude

    def Θ(self):
        return self.sr860.theta
    
    def FFT(self):
        return self.sr860.FFT
    
    def xnoize(self):
        return self.sr860.xnoize
    
    def ynoize(self):
        return self.sr860.ynoize

    def frequency(self):
        return self.sr860.frequency

    def phase(self):
        return self.sr860.phase

    def amplitude(self):
        return self.sr860.sine_voltage

    def sensitivity(self):
        return self.sr860.sensitivity

    def time_constant(self):
        return self.sr860.time_constant
    
    def input_range(self):
        return self.sr860.input_range

    def low_pass_filter_slope(self):
        return self.sr860.filter_slope

    def synchronous_filter_status(self):
        return self.sr860.filter_synchronous

    def AUX1_input(self):
        return self.sr860.aux_in_1

    def AUX2_input(self):
        return self.sr860.aux_in_2

    def AUX3_input(self):
        return self.sr860.aux_in_3

    def AUX4_input(self):
        return self.sr860.aux_in_4
    
    def dc_bias(self):
        return self.sr860.DC_bias
    
    def set_write(self, value):
        device = rm.open_resource(
            self.adress)
        device.write(value)
        device.close()

    def set_frequency(self, value=30.0):
        self.sr860.frequency = value

    def set_phase(self, value=0.0):
        self.sr860.phase = value

    def set_amplitude(self, value=0.5):
        self.sr860.sine_voltage = value

    def set_sensitivity(self, value=24):
        self.sr860.sensitivity = value

    def set_time_constant(self, value=19):
        self.sr860.time_constant = value
        
    def set_input_range(self, value = 3):
        self.sr830.input_range = value

    def set_low_pass_filter_slope(self, value=3):
        self.sr860.filter_slope = value

    def set_synchronous_filter_status(self, value=0):
        self.sr860.filter_synchronous = value

    def set_AUX1_output(self, value=0):
        self.sr860.aux_out_1 = value

    def set_AUX2_output(self, value=0):
        self.sr860.aux_out_2 = value

    def set_AUX3_output(self, value=0):
        self.sr860.aux_out_3 = value

    def set_AUX4_output(self, value=0):
        self.sr860.aux_out_4 = value
        
    def set_PULS_AUX_1(self, value=0):
        self.sr860.aux_out_1 = value
        time.sleep(0.1)
        self.sr860.aux_out_1 = 0
        
    def set_dc_bias(self, value):
        self.sr860.DC_bias = value
        
    def screen_layout(self):
        return self.sr860.screen_layout
    
    def dcmode(self):
        return self.sr860.dcmode
    
    def reference_source(self):
        return self.sr860.reference_source
    
    def reference_triggermode(self):
        return self.sr860.reference_triggermode
    
    def reference_externalinput(self):
        return self.sr860.reference_externalinput
    
    def input_signal(self):
        return self.sr860.input_signal
    
    def input_voltage_mode(self):
        return self.sr860.input_voltage_mode
    
    def input_coupling(self):
        return self.sr860.input_coupling
    
    def input_shields(self):
        return self.sr860.input_shields
    
    def input_current_gain(self):
        return self.sr860.input_current_gain
    
    def timebase(self):
        return self.sr860.gettimebase
    
    def freq_ext(self):
        return self.sr860.extfreqency
    
    def freq_detected(self):
        return self.sr860.detectedfrequency
    
    def signal_strength_indicator(self):
        return self.sr860.get_signal_strength_indicator
    
    def noise_bandwidth(self):
        return self.sr860.get_noise_bandwidth
    
    
        
def main():
    device = sr860('GPIB0::1::INSTR')
    #print(device.Write())
    #print(device.frequency())
    loggable = device.loggable
    for param in loggable:
        print(f'{param} = {getattr(device, param)()}')
    
if __name__ == '__main__':
    main()
    