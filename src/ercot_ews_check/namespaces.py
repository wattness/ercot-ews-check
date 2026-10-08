"""XML namespaces used by ERCOT External Web Services."""

EWS = "http://www.ercot.com/schema/2007-06/nodal/ews"
MESSAGE = "http://www.ercot.com/schema/2007-06/nodal/ews/message"
NOTIFICATION = "http://www.ercot.com/schema/2007-06/nodal/notification"
SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
XS = "http://www.w3.org/2001/XMLSchema"

# The namespace ERCOT's samples used before the 2007-06 schemas; no current XSD declares it.
RETIRED_EWS = "http://www.ercot.com/schema/2007-05/nodal/ews"


def q(ns: str, tag: str) -> str:
    """Clark notation: ``{namespace}tag``."""
    return f"{{{ns}}}{tag}"


def local(tag: str) -> str:
    """The local name of a Clark-notation tag."""
    return tag.rsplit("}", 1)[-1]


def namespace(tag: str) -> str:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else ""
