//! malloc and free for WebAssembly, over Rust's allocator: each block keeps its size in the word before it
use std::alloc::{alloc, dealloc, Layout};
use std::ffi::c_void;

const HEADER: usize = 8;

fn layout(size: usize) -> Layout {
	Layout::from_size_align(size + HEADER, HEADER).expect("a block's layout")
}

#[no_mangle]
pub unsafe extern "C" fn malloc(size: usize) -> *mut c_void {
	let block = alloc(layout(size));
	if block.is_null() {
		return block as *mut c_void;
	}
	(block as *mut usize).write(size);
	block.add(HEADER) as *mut c_void
}

#[no_mangle]
pub unsafe extern "C" fn free(pointer: *mut c_void) {
	if pointer.is_null() {
		return;
	}
	let block = (pointer as *mut u8).sub(HEADER);
	dealloc(block, layout((block as *mut usize).read()));
}
