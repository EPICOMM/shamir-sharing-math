use std::fmt::Debug;

use pyo3::{exceptions::PyValueError, prelude::*};

#[pymodule]
fn quinemccluskey(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(minimize, m)?)?;
    Ok(())
}

pub enum Node {
    None,
    And(Vec<Node>),
    Or(Vec<Node>),
    Not(Vec<Node>),
    Var(u8),
}

impl IntoPy<PyObject> for Node {
    fn into_py(self, py: Python<'_>) -> PyObject {
        match self {
            Node::None => ().into_py(py),
            Node::And(children) => ('&', children).into_py(py),
            Node::Or(children) => ('|', children).into_py(py),
            Node::Not(children) => ('~', children).into_py(py),
            Node::Var(idx) => idx.into_py(py),
        }
    }
}

#[pyfunction]
pub fn minimize(bits: usize, terms: Vec<u32>) -> Result<Node, PyErr> {
    if bits > 32 {
        return Err(PyValueError::new_err("too many variables"));
    }
    if terms.is_empty() {
        return Ok(Node::None);
    }
    let max = 1 << bits;
    if terms.iter().any(|&x| x >= max) {
        return Err(PyValueError::new_err("invalid terms"));
    }

    let terms = terms.iter().map(|&x| Term(x.into())).collect();
    let prime_implicants = prime_implicants(bits, terms);
    let essential_implicants = essential_implicants(bits, prime_implicants);

    todo!()
}

#[derive(Copy, Clone, Eq, PartialEq, PartialOrd, Ord)]
#[repr(transparent)]
pub struct Term(pub u64);

impl Term {
    pub const fn lower(self) -> u32 {
        self.0 as u32
    }

    pub const fn upper(self) -> u32 {
        (self.0 >> 32) as u32
    }

    pub const fn ones(self) -> u32 {
        debug_assert_eq!((self.lower() & self.upper()).count_ones(), 0);
        let masked = self.lower() & (!self.upper());
        masked.count_ones()
    }

    pub const fn try_join(self, other: Term) -> Option<Term> {
        if self.upper() != other.upper() {
            return None;
        }
        let difference = self.lower() ^ other.lower();
        if difference.count_ones() != 1 {
            return None;
        }
        let difference = difference as u64;
        let val = (self.0 & other.0) | (difference << 32);
        Some(Term(val))
    }

    pub fn permutations(self) -> Vec<u32> {
        let ones = self.upper().count_ones();
        let mut masks = Vec::with_capacity(ones as usize);
        for i in 0..32 {
            let mask = 1 << i;
            if (self.upper() & mask) != 0 {
                masks.push(mask)
            }
        }

        let mut result = Vec::with_capacity(1 << ones);
        for filter in 0..1 << ones {
            let mut sum = 0;
            for (n, mask) in masks.iter().enumerate() {
                let is_toggled = ((1 << n) & filter) >> n;
                sum += mask * is_toggled;
            }
            result.push(self.lower() | sum);
        }
        result
    }

    pub const fn rank(self) -> u32 {
        self.upper().count_ones() * 8 + self.lower().count_ones()
    }
}

impl std::fmt::Display for Term {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let low = self.lower();
        let high = self.upper();
        let mut result = String::new();
        let width = f.width().unwrap_or(32);
        if ((low | high) & !((1 << width) - 1)) != 0 {
            result.push('…');
        }
        for i in (0..width).rev() {
            let mask = 1 << i;
            result.push(match (high & mask) != 0 {
                true => match (low & mask) != 0 {
                    true => 'x', // invalid state
                    false => '-',
                },
                false => match (low & mask) != 0 {
                    true => '1',
                    false => '0',
                },
            });
        }
        write!(f, "{}", result)
    }
}

impl Debug for Term {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Term(")?;
        std::fmt::Display::fmt(&self, f)?;
        write!(f, ")")?;
        Ok(())
    }
}

pub fn prime_implicants(bits: usize, mut terms: Vec<Term>) -> Vec<Term> {
    let mut groups = vec![Vec::new(); bits + 1];
    let mut used = Vec::new();
    let mut result = Vec::new();
    loop {
        for group in &mut groups {
            group.clear();
        }
        for &term in terms.iter() {
            let n_ones = term.ones() as usize;
            groups[n_ones].push(term);
        }
        terms.clear();
        used.clear();
        for i in 0..groups.len() - 1 {
            let group = &groups[i];
            let next = &groups[i + 1];
            for &t1 in group {
                for &t2 in next {
                    if let Some(joined) = t1.try_join(t2) {
                        terms.push(joined);
                        used.push(t1);
                        used.push(t2);
                    }
                }
            }
        }
        result.extend(groups.iter().flatten().filter(|x| !used.contains(x)));
        if used.is_empty() {
            break;
        }
    }
    result.sort();
    result.dedup();
    result
}

pub fn essential_implicants(bits: usize, prime_implicants: Vec<Term>) {
    let permutations = prime_implicants
        .iter()
        .map(|&term| term.permutations())
        .collect::<Vec<_>>();
}
