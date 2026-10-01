package com.pannous.uniscript;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.lang.foreign.AddressLayout;
import java.lang.foreign.Arena;
import java.lang.foreign.FunctionDescriptor;
import java.lang.foreign.Linker;
import java.lang.foreign.MemoryLayout;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.StructLayout;
import java.lang.foreign.SymbolLookup;
import java.lang.invoke.MethodHandle;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.function.Function;

import static java.lang.foreign.MemoryLayout.PathElement.groupElement;
import static java.lang.foreign.ValueLayout.ADDRESS;
import static java.lang.foreign.ValueLayout.JAVA_INT;
import static java.lang.foreign.ValueLayout.JAVA_LONG;

/** The C ABI of c/uniscript.h, loaded from native/&lt;rid&gt;/ in the jar or the path in the property uniscript.library */
final class NativeLibrary {
	static final String LIBRARY_PROPERTY = "uniscript.library";
	private static final AddressLayout POINTER = ADDRESS;
	private static final MemoryLayout SIZE = JAVA_LONG; // size_t on every bundled platform (all 64-bit)

	static final StructLayout WARNING = MemoryLayout.structLayout(
			POINTER.withName("message"), SIZE.withName("at"));
	static final StructLayout RESULT = MemoryLayout.structLayout(
			POINTER.withName("text"), JAVA_INT.withName("error_kind"), MemoryLayout.paddingLayout(4),
			POINTER.withName("error"), POINTER.withName("error_detail"), SIZE.withName("error_at"),
			POINTER.withName("warnings"), SIZE.withName("warning_count"));
	static final StructLayout META_RUN = MemoryLayout.structLayout(
			POINTER.withName("key"), POINTER.withName("value"),
			SIZE.withName("start"), SIZE.withName("end"), SIZE.withName("at"));
	static final StructLayout STYLED = MemoryLayout.structLayout(
			POINTER.withName("text"), POINTER.withName("runs"), SIZE.withName("run_count"),
			POINTER.withName("warnings"), SIZE.withName("warning_count"));
	static final StructLayout FONT = MemoryLayout.structLayout(
			POINTER.withName("name"), POINTER.withName("lang"),
			POINTER.withName("families"), SIZE.withName("family_count"),
			POINTER.withName("features"), SIZE.withName("feature_count"));

	private static final Linker LINKER = Linker.nativeLinker();
	private static final SymbolLookup LIBRARY = SymbolLookup.libraryLookup(libraryPath(), Arena.global());

	static final MethodHandle CONVERT = function("uniscript_convert", FunctionDescriptor.of(RESULT, POINTER, JAVA_INT));
	static final MethodHandle TO_UNISCRIPT = function("uniscript_to_uniscript", FunctionDescriptor.of(POINTER, POINTER));
	static final MethodHandle HEADER = function("uniscript_header",
			FunctionDescriptor.of(JAVA_INT, POINTER, POINTER, POINTER, POINTER));
	static final MethodHandle META_RUNS = function("uniscript_meta_runs", FunctionDescriptor.of(STYLED, POINTER));
	static final MethodHandle HTML = function("uniscript_html", FunctionDescriptor.of(RESULT, POINTER));
	static final MethodHandle FONT_LOOKUP = function("uniscript_font_lookup", FunctionDescriptor.of(JAVA_INT, POINTER, POINTER));
	static final MethodHandle META_TEMPLATE = function("uniscript_meta_template", FunctionDescriptor.of(POINTER, POINTER));
	static final MethodHandle FREE = function("uniscript_free", FunctionDescriptor.ofVoid(POINTER));
	static final MethodHandle RESULT_FREE = function("uniscript_result_free", FunctionDescriptor.ofVoid(POINTER));
	static final MethodHandle STYLED_FREE = function("uniscript_styled_free", FunctionDescriptor.ofVoid(POINTER));
	static final MethodHandle FONT_FREE = function("uniscript_font_free", FunctionDescriptor.ofVoid(POINTER));

	private NativeLibrary() {}

	private static MethodHandle function(String name, FunctionDescriptor descriptor) {
		MemorySegment symbol = LIBRARY.find(name).orElseThrow(() -> new UnsatisfiedLinkError("no symbol " + name));
		return LINKER.downcallHandle(symbol, descriptor);
	}

	/** osx-arm64, osx-x64, linux-x64, linux-arm64, win-x64: the runtime identifiers of make -C c/ffi natives */
	static String platform() {
		String os = System.getProperty("os.name").toLowerCase(Locale.ROOT);
		String arch = System.getProperty("os.arch");
		String system = os.startsWith("mac") ? "osx" : os.startsWith("windows") ? "win" : "linux";
		return system + "-" + (arch.equals("aarch64") || arch.equals("arm64") ? "arm64" : "x64");
	}

	static String libraryName() {
		return switch (platform().substring(0, platform().indexOf('-'))) {
			case "osx" -> "libuniscript.dylib";
			case "win" -> "uniscript.dll";
			default -> "libuniscript.so";
		};
	}

	private static Path libraryPath() {
		String configured = System.getProperty(LIBRARY_PROPERTY);
		return configured != null ? Path.of(configured) : extractedLibrary();
	}

	/** The bundled library copied to a temporary directory: a library inside a jar cannot be loaded in place */
	private static Path extractedLibrary() {
		String resource = "/native/" + platform() + "/" + libraryName();
		try (InputStream library = NativeLibrary.class.getResourceAsStream(resource)) {
			if (library == null) {
				throw new UnsatisfiedLinkError("uniscript bundles no native library for " + platform() + " (" + resource
						+ "); set -D" + LIBRARY_PROPERTY + "=<path to " + libraryName() + ">");
			}
			Path directory = Files.createTempDirectory("uniscript-");
			Path file = directory.resolve(libraryName());
			Files.copy(library, file);
			file.toFile().deleteOnExit();
			directory.toFile().deleteOnExit();
			return file;
		} catch (IOException failure) {
			throw new UncheckedIOException("cannot extract " + resource, failure);
		}
	}

	static long offset(StructLayout layout, String field) {
		return layout.byteOffset(groupElement(field));
	}

	static MemorySegment pointer(MemorySegment struct, StructLayout layout, String field) {
		return struct.get(ADDRESS, offset(layout, field));
	}

	static long size(MemorySegment struct, StructLayout layout, String field) {
		return struct.get(JAVA_LONG, offset(layout, field));
	}

	/** A NUL-terminated UTF-8 string the library owns; null for NULL */
	static String string(MemorySegment pointer) {
		return pointer.equals(MemorySegment.NULL) ? null : pointer.reinterpret(Long.MAX_VALUE).getString(0);
	}

	static String string(MemorySegment struct, StructLayout layout, String field) {
		return string(pointer(struct, layout, field));
	}

	/** The count elements of a C array of layout, each read by element */
	static <T> List<T> array(MemorySegment first, long count, MemoryLayout layout, Function<MemorySegment, T> element) {
		List<T> items = new ArrayList<>((int) count);
		MemorySegment elements = first.reinterpret(count * layout.byteSize());
		for (long index = 0; index < count; index++) {
			items.add(element.apply(elements.asSlice(index * layout.byteSize(), layout.byteSize())));
		}
		return List.copyOf(items);
	}
}
