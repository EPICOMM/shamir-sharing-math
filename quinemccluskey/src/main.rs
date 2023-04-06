use quinemccluskey::*;

fn main() {
    const TERMS: &[u32] = &[
        0b0100,
        0b1000,
        0b1001,
        0b1010,
        0b1100,
        0b1011,
        0b1110,
        0b1111
    ];
    // const TERMS: &[u32] = &[
    //     3, 4, 5, 7, 9, 13, 14, 15
    // ];

    let terms = TERMS.iter().map(|&x| Term(x.into())).collect();
    let prime_implicants = prime_implicants(4, terms);
    println!("{:#4?}", prime_implicants);
    let essential_implicants = essential_implicants(4, prime_implicants);
    println!("{:#4?}", essential_implicants);
}