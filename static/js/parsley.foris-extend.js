window.ParsleyConfig = window.ParsleyConfig || {};

(function ($) {
  window.ParsleyConfig = $.extend( true, {}, window.ParsleyConfig, {
    validators: {
      type: function () {
        return {
          validate: function ( val, type ) {
            var regExp;
            switch (type) {
              case 'ipv4':
                var bytes = val.split(".");
                if (bytes.length != 4)
                  return false;
                var intRE = /^[0-9]+$/;
                for (var i = 0; i < bytes.length; i++) {
                  // check it's an integer number, not exponential format, hex number etc...
                  if (!intRE.test(bytes[i]))
                    return false;
                  if (bytes[i] < 0 || bytes[i] > 255)
                    return false;
                }
                return true;
              case 'ipv6':
                // source: http://home.deds.nl/~aeron/regex/
                regExp = /^((?=.*::)(?!.*::.+::)(::)?([\dA-F]{1,4}:(:|\b)|){5}|([\dA-F]{1,4}:){6})((([\dA-F]{1,4}((?!\3)::|:\b|$))|(?!\2\3)){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})$/i;
                break;
              case 'ipv6prefix':
                // source: http://home.deds.nl/~aeron/regex/
                regExp = /^((?=.*::)(?!.*::.+::)(::)?([\dA-F]{1,4}:(:|\b)|){5}|([\dA-F]{1,4}:){6})((([\dA-F]{1,4}((?!\3)::|:\b|$))|(?!\2\3)){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})$/i;
                var splitVal = val.split("/");
                if (splitVal.length != 2) return false;
                if (!/^(\d|[1-9]\d|1[0-1]\d|12[0-8])$/.test(splitVal[1])) return false;
                val = splitVal[0];
                break;
              case 'macaddress':
                regExp = /^([0-9A-F]{2}:){5}([0-9A-F]{2})$/i;
                break;
              default:
                return false;
            }

            return val !== '' ? regExp.test(val) : false;
          }
          , priority: 32
        }
      }
    },
    messages: {
      type: {
        ipv4: "This is not a valid IPv4 address.",
        ipv6: "This is not a valid IPv6 address.",
        ipv6prefix: "This is not a valid IPv6 prefix.",
        macaddress: "This is not a valid MAC address."
      }
    }
  });
}(window.jQuery || window.Zepto));
