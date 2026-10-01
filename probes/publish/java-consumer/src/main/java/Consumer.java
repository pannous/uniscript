import com.pannous.uniscript.ffi.Uniscript;

public class Consumer {
	public static void main(String[] arguments) {
		String text = Uniscript.toUnicode(arguments[0]);
		System.out.println(text + " | " + Uniscript.toUniscript(text));
	}
}
