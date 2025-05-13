- have to figure out how to get types that the settings object depends on into the dynamic module created by
  `build_command` (enum classes, Literal, etc)
- consider an `unpack_path` parameter for `_x` methods that serialize the response by extracting a JMESPath from the
  response
