using System;
using Pannous;

var text = Uniscript.ToUnicode(args[0]);
Console.WriteLine($"{text} | {Uniscript.ToUniscript(text)}");
